"""
MaintenanceHub — Ticket Views
Dashboards, ticket CRUD, workflow actions, comments, attachments.
"""
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.decorators.http import require_POST, require_GET
from django.utils.decorators import method_decorator
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db.models import Q, Count, Avg
from django.core.paginator import Paginator
from django.utils import timezone

from apps.accounts.mixins import OrgRequiredMixin, ManagerRequiredMixin, AdminRequiredMixin
from apps.accounts.models import UserRole
from apps.audit.models import AuditLog, AuditAction

from .models import (
    Ticket, TicketStatus, TicketActivity, ActivityType,
    TicketComment, TicketAttachment, Category, Priority,
    VALID_TRANSITIONS,
)
from .forms import TicketCreateForm, TicketUpdateForm, CommentForm, AssignTicketForm
from .services import TicketService


# ── Dashboard Views ────────────────────────────────────────────────────────────

class DashboardView(OrgRequiredMixin, View):
    """
    Role-aware dashboard router.
    Users see their tickets; staff see their workload;
    managers/admins see the full operations dashboard.
    """

    def get(self, request):
        user = request.user

        if user.role in (UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN, UserRole.MANAGER):
            return self._admin_dashboard(request)
        elif user.role == UserRole.STAFF:
            return self._staff_dashboard(request)
        else:
            return self._user_dashboard(request)

    def _user_dashboard(self, request):
        tickets = Ticket.objects.filter(
            organization=request.org,
            created_by=request.user,
        ).select_related("category", "location", "assigned_to").order_by("-created_at")

        stats = {
            "open": tickets.filter(status__in=["submitted", "triaged", "assigned"]).count(),
            "in_progress": tickets.filter(status="in_progress").count(),
            "awaiting_verification": tickets.filter(status="verification_pending").count(),
            "resolved": tickets.filter(status__in=["resolved", "closed"]).count(),
            "total": tickets.count(),
        }

        recent = tickets[:10]
        return render(request, "dashboard/user.html", {
            "tickets": recent,
            "stats": stats,
        })

    def _staff_dashboard(self, request):
        from django.utils import timezone
        today = timezone.now().date()

        assigned_tickets = Ticket.objects.filter(
            organization=request.org,
            assigned_to=request.user,
        ).exclude(
            status__in=[TicketStatus.CLOSED, TicketStatus.CANCELLED]
        ).select_related("category", "location", "created_by").order_by("sla_resolution_due", "-priority")

        stats = {
            "assigned_today": assigned_tickets.count(),
            "critical": assigned_tickets.filter(priority="critical").count(),
            "overdue": assigned_tickets.filter(sla_resolution_due__lt=timezone.now()).count(),
            "in_progress": assigned_tickets.filter(status="in_progress").count(),
        }

        return render(request, "dashboard/staff.html", {
            "assigned_tickets": assigned_tickets[:20],
            "stats": stats,
        })

    def _admin_dashboard(self, request):
        from django.utils import timezone
        import datetime

        org = request.org
        base_qs = Ticket.objects.filter(organization=org)

        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        stats = {
            "total": base_qs.count(),
            "open": base_qs.filter(status__in=["submitted", "triaged", "assigned"]).count(),
            "in_progress": base_qs.filter(status="in_progress").count(),
            "resolved_today": base_qs.filter(resolved_at__gte=today_start).count(),
            "overdue": base_qs.filter(
                sla_resolution_due__lt=now,
                status__in=["submitted", "triaged", "assigned", "in_progress"]
            ).count(),
            "critical": base_qs.filter(
                priority="critical",
                status__in=["submitted", "triaged", "assigned", "in_progress"]
            ).count(),
        }

        # Recent tickets
        recent_tickets = base_qs.select_related(
            "category", "location", "created_by", "assigned_to"
        ).order_by("-created_at")[:10]

        # Critical & overdue tickets
        critical_tickets = base_qs.filter(
            priority="critical",
            status__in=["submitted", "triaged", "assigned", "in_progress"]
        ).select_related("category", "location", "assigned_to").order_by("sla_resolution_due")[:5]

        return render(request, "dashboard/admin.html", {
            "stats": stats,
            "recent_tickets": recent_tickets,
            "critical_tickets": critical_tickets,
        })


class MyTicketsView(OrgRequiredMixin, View):
    """User's own tickets list."""

    def get(self, request):
        tickets = Ticket.objects.filter(
            organization=request.org,
            created_by=request.user,
        ).select_related("category", "location", "assigned_to").order_by("-created_at")

        # Status filter
        status_filter = request.GET.get("status", "")
        if status_filter:
            tickets = tickets.filter(status=status_filter)

        paginator = Paginator(tickets, 20)
        page = paginator.get_page(request.GET.get("page", 1))

        return render(request, "tickets/my_tickets.html", {
            "page_obj": page,
            "status_filter": status_filter,
            "statuses": TicketStatus.choices,
        })


class AllTicketsView(ManagerRequiredMixin, View):
    """Management ticket table — all tickets with full filtering."""

    def get(self, request):
        qs = Ticket.objects.filter(organization=request.org).select_related(
            "category", "location", "created_by", "assigned_to"
        )

        # Filters
        q = request.GET.get("q", "").strip()
        status = request.GET.get("status", "")
        priority = request.GET.get("priority", "")
        assigned = request.GET.get("assigned", "")
        category = request.GET.get("category", "")
        date_from = request.GET.get("date_from", "")
        date_to = request.GET.get("date_to", "")
        sort = request.GET.get("sort", "-created_at")

        if q:
            qs = qs.filter(
                Q(ticket_number__icontains=q) |
                Q(title__icontains=q) |
                Q(description__icontains=q) |
                Q(created_by__full_name__icontains=q) |
                Q(location__name__icontains=q)
            )
        if status:
            qs = qs.filter(status=status)
        if priority:
            qs = qs.filter(priority=priority)
        if assigned:
            if assigned == "unassigned":
                qs = qs.filter(assigned_to__isnull=True)
            else:
                qs = qs.filter(assigned_to_id=assigned)
        if category:
            qs = qs.filter(category_id=category)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        # Sorting
        allowed_sorts = [
            "created_at", "-created_at", "priority", "-priority",
            "status", "-status", "sla_resolution_due", "-sla_resolution_due"
        ]
        if sort not in allowed_sorts:
            sort = "-created_at"
        qs = qs.order_by(sort)

        paginator = Paginator(qs, 25)
        page = paginator.get_page(request.GET.get("page", 1))

        # Filter options
        from apps.accounts.models import User
        staff_members = User.objects.filter(
            organization=request.org,
            role__in=[UserRole.STAFF, UserRole.MANAGER]
        )
        categories = Category.objects.filter(organization=request.org, parent__isnull=True, is_active=True)

        # HTMX partial update
        if request.headers.get("HX-Request"):
            return render(request, "tickets/partials/ticket_table.html", {
                "page_obj": page,
                "sort": sort,
            })

        return render(request, "tickets/all_tickets.html", {
            "page_obj": page,
            "staff_members": staff_members,
            "categories": categories,
            "statuses": TicketStatus.choices,
            "priorities": Priority.choices,
            "sort": sort,
            "filters": {
                "q": q, "status": status, "priority": priority,
                "assigned": assigned, "category": category,
                "date_from": date_from, "date_to": date_to,
            },
        })


class KanbanView(ManagerRequiredMixin, View):
    """Kanban board view — tickets grouped by status."""

    KANBAN_COLUMNS = [
        (TicketStatus.SUBMITTED, "Submitted"),
        (TicketStatus.TRIAGED, "Triaged"),
        (TicketStatus.ASSIGNED, "Assigned"),
        (TicketStatus.IN_PROGRESS, "In Progress"),
        (TicketStatus.ON_HOLD, "On Hold"),
        (TicketStatus.RESOLVED, "Resolved"),
    ]

    def get(self, request):
        base_qs = Ticket.objects.filter(organization=request.org).select_related(
            "category", "location", "assigned_to"
        ).order_by("sla_resolution_due", "-priority")

        columns = []
        for status, label in self.KANBAN_COLUMNS:
            tickets = base_qs.filter(status=status)[:20]
            columns.append({
                "status": status,
                "label": label,
                "tickets": tickets,
                "count": base_qs.filter(status=status).count(),
            })

        return render(request, "tickets/kanban.html", {"columns": columns})


class KanbanMoveView(ManagerRequiredMixin, View):
    """HTMX endpoint — drag-and-drop a ticket to a new Kanban column."""

    def post(self, request, pk):
        ticket = get_object_or_404(Ticket, pk=pk, organization=request.org)
        new_status = request.POST.get("status")

        allowed_statuses = {s for s, _ in TicketStatus.choices}
        if new_status not in allowed_statuses:
            return JsonResponse({"error": "Invalid status"}, status=400)

        # Only managers+ can move via kanban; apply same transition rules
        allowed_transitions = VALID_TRANSITIONS.get(ticket.status, set())
        if new_status not in allowed_transitions and new_status != ticket.status:
            return JsonResponse({"error": "Transition not allowed"}, status=400)

        if new_status != ticket.status:
            old_status = ticket.status
            ticket.transition_to(new_status, user=request.user)
            status_labels = dict(TicketStatus.choices)
            TicketActivity.create(
                ticket=ticket,
                actor=request.user,
                activity_type=ActivityType.STATUS_CHANGED,
                description=f"Moved on Kanban from {status_labels.get(old_status, old_status)} "
                            f"to {status_labels.get(new_status, new_status)}",
                metadata={"from": old_status, "to": new_status, "via": "kanban"},
            )
            AuditLog.log(request, AuditAction.STATUS_CHANGE, ticket,
                         old_value={"status": old_status},
                         new_value={"status": new_status})

            from apps.core.ws_utils import broadcast_ticket_update
            broadcast_ticket_update(ticket, event_type="kanban_move",
                                    extra={"from": old_status, "to": new_status})

        return JsonResponse({"ok": True, "ticket_number": ticket.ticket_number,
                             "new_status": ticket.status})


# ── Ticket CRUD ────────────────────────────────────────────────────────────────

class CreateTicketView(OrgRequiredMixin, View):
    """Ticket creation with attachment support."""
    template_name = "tickets/create.html"

    def get(self, request):
        form = TicketCreateForm(organization=request.org)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = TicketCreateForm(request.POST, request.FILES, organization=request.org)
        if form.is_valid():
            ticket = TicketService.create_ticket(
                form=form,
                user=request.user,
                organization=request.org,
                files=request.FILES.getlist("attachments"),
            )
            messages.success(
                request,
                f"Your request has been created. Ticket: {ticket.ticket_number}"
            )
            return redirect("dashboard:ticket-detail", pk=ticket.pk)
        return render(request, self.template_name, {"form": form})


class TicketDetailView(OrgRequiredMixin, View):
    """Full ticket detail with timeline and comments."""

    def get(self, request, pk):
        ticket = get_object_or_404(
            Ticket.objects.select_related(
                "created_by", "assigned_to", "category", "location", "asset", "assigned_team"
            ).prefetch_related("attachments", "status_history"),
            pk=pk,
            organization=request.org,
        )

        # Access control: users can only see their own tickets unless staff+
        if (request.user.role == UserRole.USER and
                ticket.created_by != request.user):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied

        # Activity timeline
        activities_qs = ticket.activities.all()
        if request.user.role == UserRole.USER:
            activities_qs = activities_qs.filter(is_internal=False)
        activities = activities_qs.select_related("actor").order_by("timestamp")

        # Comments
        comments_qs = ticket.comments.select_related("author")
        if request.user.role == UserRole.USER:
            comments_qs = comments_qs.filter(is_internal=False)
        comments = comments_qs.order_by("created_at")

        # Allowed next transitions for current user
        allowed_transitions = self._get_allowed_transitions(ticket, request.user)

        # Forms
        comment_form = CommentForm(user=request.user)
        assign_form = AssignTicketForm(organization=request.org) if request.user.can_manage else None

        return render(request, "tickets/detail.html", {
            "ticket": ticket,
            "activities": activities,
            "comments": comments,
            "comment_form": comment_form,
            "assign_form": assign_form,
            "allowed_transitions": allowed_transitions,
            "VALID_TRANSITIONS": VALID_TRANSITIONS,
        })

    def _get_allowed_transitions(self, ticket, user):
        """Return list of valid transitions the user can make."""
        all_transitions = VALID_TRANSITIONS.get(ticket.status, set())

        if user.role == UserRole.USER:
            # Users can only verify resolution or rate
            return all_transitions & {TicketStatus.REOPENED}
        elif user.role == UserRole.STAFF:
            # Staff can mark in-progress, resolved, on-hold
            return all_transitions & {
                TicketStatus.IN_PROGRESS, TicketStatus.ON_HOLD,
                TicketStatus.RESOLVED, TicketStatus.VERIFICATION_PENDING
            }
        else:
            # Managers/admins can make any valid transition
            return all_transitions


class TicketUpdateView(ManagerRequiredMixin, View):
    """Update ticket metadata (priority, category, location)."""

    def post(self, request, pk):
        ticket = get_object_or_404(Ticket, pk=pk, organization=request.org)
        form = TicketUpdateForm(request.POST, instance=ticket, organization=request.org)
        if form.is_valid():
            old_priority = ticket.priority
            updated = form.save(commit=False)

            if old_priority != updated.priority:
                TicketActivity.create(
                    ticket=updated,
                    actor=request.user,
                    activity_type=ActivityType.PRIORITY_CHANGED,
                    description=f"Priority changed from {old_priority} to {updated.priority}",
                    metadata={"from": old_priority, "to": updated.priority},
                )
                AuditLog.log(request, AuditAction.PRIORITY_CHANGE, ticket,
                             old_value={"priority": old_priority},
                             new_value={"priority": updated.priority})

            updated.save()
            messages.success(request, "Ticket updated.")

            if request.headers.get("HX-Request"):
                return HttpResponse('<div class="text-green-600 text-sm">✓ Saved</div>')

        return redirect("dashboard:ticket-detail", pk=pk)


# ── Ticket Workflow Actions ─────────────────────────────────────────────────────

class TicketTransitionView(OrgRequiredMixin, View):
    """Handle status transitions for a ticket."""

    def post(self, request, pk):
        ticket = get_object_or_404(Ticket, pk=pk, organization=request.org)
        new_status = request.POST.get("status")
        note = request.POST.get("note", "")

        # Verify user has permission
        allowed = self._get_allowed_transitions(ticket, request.user)
        if new_status not in allowed:
            messages.error(request, "You cannot perform this action.")
            return redirect("dashboard:ticket-detail", pk=pk)

        try:
            ticket.transition_to(new_status, user=request.user, note=note)

            # Log activity
            activity_map = {
                TicketStatus.IN_PROGRESS: ActivityType.STATUS_CHANGED,
                TicketStatus.RESOLVED: ActivityType.RESOLVED,
                TicketStatus.CLOSED: ActivityType.CLOSED,
                TicketStatus.REOPENED: ActivityType.REOPENED,
                TicketStatus.VERIFICATION_PENDING: ActivityType.STATUS_CHANGED,
            }
            atype = activity_map.get(new_status, ActivityType.STATUS_CHANGED)
            status_labels = dict(TicketStatus.choices)
            TicketActivity.create(
                ticket=ticket,
                actor=request.user,
                activity_type=atype,
                description=f"Status changed to {status_labels.get(new_status, new_status)}",
                metadata={"new_status": new_status, "note": note},
            )

            # Send notifications async
            from apps.notifications.tasks import notify_ticket_status_change
            notify_ticket_status_change.delay(ticket.pk, new_status, request.user.pk)

            # Broadcast real-time WebSocket update
            from apps.core.ws_utils import broadcast_ticket_update
            broadcast_ticket_update(ticket, event_type="status_changed", extra={"new_status": new_status})

            messages.success(request, f"Status updated to {status_labels.get(new_status, new_status)}.")
        except Exception as e:
            messages.error(request, str(e))

        return redirect("dashboard:ticket-detail", pk=pk)

    def _get_allowed_transitions(self, ticket, user):
        all_t = VALID_TRANSITIONS.get(ticket.status, set())
        if user.role == UserRole.USER:
            return all_t & {TicketStatus.REOPENED}
        elif user.role == UserRole.STAFF:
            return all_t & {TicketStatus.IN_PROGRESS, TicketStatus.ON_HOLD,
                            TicketStatus.RESOLVED, TicketStatus.VERIFICATION_PENDING}
        return all_t


class AssignTicketView(ManagerRequiredMixin, View):
    """Assign a ticket to a staff member."""

    def post(self, request, pk):
        ticket = get_object_or_404(Ticket, pk=pk, organization=request.org)
        form = AssignTicketForm(request.POST, organization=request.org)

        if form.is_valid():
            old_assignee = ticket.assigned_to
            new_assignee = form.cleaned_data["assigned_to"]
            team = form.cleaned_data.get("team")

            ticket.assigned_to = new_assignee
            ticket.assigned_team = team
            if ticket.status == TicketStatus.SUBMITTED:
                ticket.status = TicketStatus.ASSIGNED
                ticket.assigned_at = timezone.now()

            ticket.save()

            action = ActivityType.REASSIGNED if old_assignee else ActivityType.ASSIGNED
            TicketActivity.create(
                ticket=ticket,
                actor=request.user,
                activity_type=action,
                description=f"Assigned to {new_assignee.display_name}",
                metadata={"assignee_id": new_assignee.pk, "assignee_name": new_assignee.display_name},
            )

            # Notify assignee
            from apps.notifications.tasks import notify_ticket_assigned
            notify_ticket_assigned.delay(ticket.pk, new_assignee.pk, request.user.pk)

            messages.success(request, f"Ticket assigned to {new_assignee.display_name}.")

        if request.headers.get("HX-Request"):
            return render(request, "tickets/partials/assignment_panel.html", {"ticket": ticket})

        return redirect("dashboard:ticket-detail", pk=pk)


class AddCommentView(OrgRequiredMixin, View):
    """Add a comment or internal note to a ticket."""

    def post(self, request, pk):
        ticket = get_object_or_404(Ticket, pk=pk, organization=request.org)

        # Access check
        if (request.user.role == UserRole.USER and ticket.created_by != request.user):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied

        form = CommentForm(request.POST, user=request.user)
        if form.is_valid():
            is_internal = form.cleaned_data.get("is_internal", False)
            # Users cannot create internal notes
            if request.user.role == UserRole.USER:
                is_internal = False

            comment = TicketComment.objects.create(
                ticket=ticket,
                author=request.user,
                body=form.cleaned_data["body"],
                is_internal=is_internal,
            )

            # Record first response timestamp
            if not ticket.first_response_at and request.user != ticket.created_by:
                ticket.first_response_at = timezone.now()
                ticket.save(update_fields=["first_response_at"])

            atype = ActivityType.INTERNAL_NOTE if is_internal else ActivityType.COMMENT_ADDED
            TicketActivity.create(
                ticket=ticket,
                actor=request.user,
                activity_type=atype,
                description=f"{'Internal note' if is_internal else 'Comment'} added",
                is_internal=is_internal,
            )

            # Notify
            from apps.notifications.tasks import notify_comment_added
            notify_comment_added.delay(ticket.pk, comment.pk, request.user.pk)

            # Broadcast real-time WebSocket update
            from apps.core.ws_utils import broadcast_comment_added
            broadcast_comment_added(ticket, comment)

            if request.headers.get("HX-Request"):
                return render(request, "tickets/partials/comment.html", {
                    "comment": comment,
                    "user": request.user,
                })

        return redirect("dashboard:ticket-detail", pk=pk)


class UploadAttachmentView(OrgRequiredMixin, View):
    """Upload an attachment to a ticket."""

    MAX_SIZE = 10 * 1024 * 1024  # 10 MB

    def post(self, request, pk):
        from django.conf import settings
        ticket = get_object_or_404(Ticket, pk=pk, organization=request.org)
        f = request.FILES.get("file")

        if not f:
            return JsonResponse({"error": "No file provided."}, status=400)

        if f.size > self.MAX_SIZE:
            return JsonResponse({"error": f"File too large. Maximum is 10 MB."}, status=400)

        # Validate by magic bytes (not client-supplied MIME type)
        try:
            from apps.core.file_utils import validate_file_magic
            detected_type = validate_file_magic(f)
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=400)

        attachment = TicketAttachment.objects.create(
            ticket=ticket,
            uploaded_by=request.user,
            file=f,
            original_filename=f.name,
            file_size=f.size,
            content_type=detected_type,  # Use validated type, not client-supplied
            is_evidence=request.POST.get("is_evidence", "false") == "true",
        )

        TicketActivity.create(
            ticket=ticket,
            actor=request.user,
            activity_type=ActivityType.ATTACHMENT_ADDED,
            description=f"Attachment added: {f.name}",
        )

        if request.headers.get("HX-Request"):
            return render(request, "tickets/partials/attachment_item.html", {
                "attachment": attachment,
            })

        return JsonResponse({"ok": True, "id": attachment.pk})


class RateTicketView(OrgRequiredMixin, View):
    """Allow the creator to rate a resolved ticket."""

    def post(self, request, pk):
        ticket = get_object_or_404(Ticket, pk=pk, organization=request.org, created_by=request.user)

        if ticket.status not in (TicketStatus.RESOLVED, TicketStatus.VERIFICATION_PENDING,
                                  TicketStatus.CLOSED):
            messages.error(request, "You can only rate resolved tickets.")
            return redirect("dashboard:ticket-detail", pk=pk)

        rating = int(request.POST.get("rating", 0))
        comment = request.POST.get("comment", "")

        if 1 <= rating <= 5:
            ticket.rating = rating
            ticket.rating_comment = comment
            if ticket.status != TicketStatus.CLOSED:
                ticket.status = TicketStatus.CLOSED
                ticket.closed_at = timezone.now()
            ticket.save()

            TicketActivity.create(
                ticket=ticket,
                actor=request.user,
                activity_type=ActivityType.RATED,
                description=f"Service rated {rating}/5 stars",
                metadata={"rating": rating, "comment": comment},
            )

            # Notify assigned staff member of the rating
            try:
                from apps.notifications.tasks import notify_ticket_rated
                notify_ticket_rated.delay(ticket.pk, rating, comment)
            except Exception:
                pass  # Never let notification failure break the rating flow

            messages.success(request, "Thank you for your feedback!")

        return redirect("dashboard:ticket-detail", pk=pk)


class SearchView(OrgRequiredMixin, View):
    """Global search — returns HTMX partial or JSON."""

    def get(self, request):
        q = request.GET.get("q", "").strip()

        if not q or len(q) < 2:
            if request.headers.get("HX-Request"):
                return HttpResponse("")
            return JsonResponse({"results": []})

        tickets = Ticket.objects.filter(
            organization=request.org,
        ).filter(
            Q(ticket_number__icontains=q) |
            Q(title__icontains=q) |
            Q(description__icontains=q)
        ).select_related("category", "location")[:8]

        # Users only see their own tickets in search
        if request.user.role == UserRole.USER:
            tickets = tickets.filter(created_by=request.user)

        if request.headers.get("HX-Request"):
            return render(request, "tickets/partials/search_results.html", {
                "tickets": tickets,
                "query": q,
            })

        results = [{"id": t.pk, "number": t.ticket_number, "title": t.title} for t in tickets]
        return JsonResponse({"results": results})


class DeleteCommentView(OrgRequiredMixin, View):
    """Soft-delete a comment. Only the author or a manager+ can delete."""

    def post(self, request, pk, comment_pk):
        ticket = get_object_or_404(Ticket, pk=pk, organization=request.org)
        comment = get_object_or_404(TicketComment, pk=comment_pk, ticket=ticket)

        can_delete = (
            comment.author == request.user or
            request.user.role in (UserRole.MANAGER, UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)
        )
        if not can_delete:
            if request.headers.get("HX-Request"):
                return HttpResponse('<span class="text-red-600 text-sm">Permission denied</span>', status=403)
            messages.error(request, "You cannot delete this comment.")
            return redirect("dashboard:ticket-detail", pk=pk)

        comment.soft_delete(user=request.user)
        TicketActivity.create(
            ticket=ticket,
            actor=request.user,
            activity_type=ActivityType.COMMENT_ADDED,
            description="Comment deleted",
            metadata={"comment_pk": comment_pk},
        )
        AuditLog.log(request, AuditAction.COMMENT_ADD, ticket,
                     old_value={"comment_pk": comment_pk, "deleted": True})

        if request.headers.get("HX-Request"):
            return HttpResponse('<p class="text-sm italic" style="color:var(--text-muted);">[Comment deleted]</p>')

        messages.success(request, "Comment deleted.")
        return redirect("dashboard:ticket-detail", pk=pk)


class BulkTicketActionView(ManagerRequiredMixin, View):
    """
    Bulk action endpoint for the ticket list.
    Supports: assign, close, change-priority.
    Expects POST with ticket_ids (comma-separated) and action.
    """

    ALLOWED_ACTIONS = {"assign", "close", "set_priority"}

    def post(self, request):
        action = request.POST.get("action", "").strip()
        raw_ids = request.POST.get("ticket_ids", "")
        try:
            ids = [int(i) for i in raw_ids.split(",") if i.strip().isdigit()]
        except ValueError:
            return JsonResponse({"error": "Invalid ticket IDs"}, status=400)

        if not ids:
            return JsonResponse({"error": "No tickets selected"}, status=400)
        if action not in self.ALLOWED_ACTIONS:
            return JsonResponse({"error": "Unknown action"}, status=400)

        tickets = Ticket.objects.filter(pk__in=ids, organization=request.org)
        affected = tickets.count()

        if action == "close":
            from django.utils import timezone as tz
            for ticket in tickets.exclude(status=TicketStatus.CLOSED):
                try:
                    ticket.transition_to(TicketStatus.CLOSED, user=request.user)
                    TicketActivity.create(
                        ticket=ticket, actor=request.user,
                        activity_type=ActivityType.CLOSED,
                        description="Bulk closed",
                        metadata={"via": "bulk_action"},
                    )
                except Exception:
                    pass

        elif action == "assign":
            from apps.accounts.models import User
            assignee_id = request.POST.get("assignee_id")
            try:
                assignee = User.objects.get(pk=assignee_id, organization=request.org)
            except User.DoesNotExist:
                return JsonResponse({"error": "Assignee not found"}, status=400)
            for ticket in tickets:
                old_assignee = ticket.assigned_to
                ticket.assigned_to = assignee
                ticket.save(update_fields=["assigned_to"])
                TicketActivity.create(
                    ticket=ticket, actor=request.user,
                    activity_type=ActivityType.ASSIGNED,
                    description=f"Bulk assigned to {assignee.display_name}",
                    metadata={"assignee": assignee.pk, "via": "bulk_action"},
                )

        elif action == "set_priority":
            new_priority = request.POST.get("priority", "")
            valid_priorities = {p for p, _ in Priority.choices}
            if new_priority not in valid_priorities:
                return JsonResponse({"error": "Invalid priority"}, status=400)
            tickets.update(priority=new_priority)
            for ticket in tickets:
                TicketActivity.create(
                    ticket=ticket, actor=request.user,
                    activity_type=ActivityType.PRIORITY_CHANGED,
                    description=f"Bulk priority set to {new_priority}",
                    metadata={"priority": new_priority, "via": "bulk_action"},
                )

        AuditLog.log(request, AuditAction.BULK_ACTION, None,
                     new_value={"action": action, "ticket_ids": ids, "affected": affected})

        if request.headers.get("HX-Request"):
            messages.success(request, f"Bulk action '{action}' applied to {affected} ticket(s).")
            return HttpResponse(
                '<div class="text-green-600 text-sm font-medium">'
                f'✓ Applied to {affected} ticket(s) — <a href="" class="underline">Refresh</a></div>'
            )

        return JsonResponse({"ok": True, "affected": affected})
