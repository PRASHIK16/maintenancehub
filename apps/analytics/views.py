"""
MaintenanceHub — Analytics Views
Charts, metrics, SLA reports, staff performance.
"""
import csv
import json
from datetime import timedelta
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.db.models import Count, Avg, Q, F, ExpressionWrapper, DurationField
from django.utils import timezone

from apps.accounts.mixins import ManagerRequiredMixin
from apps.tickets.models import Ticket, TicketStatus, Priority


class AnalyticsOverviewView(ManagerRequiredMixin, View):
    """Main analytics dashboard."""

    def get(self, request):
        org = request.org

        # Support custom date range OR period preset
        date_from = request.GET.get("date_from")
        date_to = request.GET.get("date_to")
        if date_from and date_to:
            try:
                from datetime import datetime
                since = timezone.make_aware(datetime.strptime(date_from, "%Y-%m-%d"))
                until = timezone.make_aware(datetime.strptime(date_to, "%Y-%m-%d").replace(
                    hour=23, minute=59, second=59
                ))
                period = None
            except ValueError:
                since = timezone.now() - timedelta(days=30)
                until = timezone.now()
                period = 30
        else:
            period = int(request.GET.get("period", 30))  # days
            since = timezone.now() - timedelta(days=period)
            until = timezone.now()

        base_qs = Ticket.objects.filter(organization=org, created_at__gte=since, created_at__lte=until)

        # ── Summary metrics ──
        total = base_qs.count()
        closed = base_qs.filter(status__in=[TicketStatus.CLOSED, TicketStatus.RESOLVED]).count()
        resolution_rate = round((closed / total * 100) if total else 0, 1)

        overdue = Ticket.objects.filter(
            organization=org,
            sla_resolution_due__lt=timezone.now(),
            status__in=["submitted", "triaged", "assigned", "in_progress"],
        ).count()

        # Average resolution time (hours) for closed tickets
        closed_qs = base_qs.filter(
            status__in=[TicketStatus.CLOSED, TicketStatus.RESOLVED],
            resolved_at__isnull=False,
        )
        avg_hours = None
        if closed_qs.exists():
            total_hours = sum(
                (t.resolved_at - t.created_at).total_seconds() / 3600
                for t in closed_qs.select_related()[:500]
                if t.resolved_at
            )
            avg_hours = round(total_hours / closed_qs.count(), 1)

        sla_met = base_qs.filter(sla_resolution_met=True).count()
        sla_total = base_qs.filter(sla_resolution_met__isnull=False).count()
        sla_rate = round((sla_met / sla_total * 100) if sla_total else 0, 1)

        # ── Tickets by priority ──
        by_priority = list(
            base_qs.values("priority")
            .annotate(count=Count("id"))
            .order_by("priority")
        )

        # ── Tickets by status ──
        by_status = list(
            base_qs.values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )

        # ── Tickets by category ──
        by_category = list(
            base_qs.exclude(category__isnull=True)
            .values("category__name")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        # ── Daily trend (last 14 days) ──
        daily_trend = []
        for i in range(13, -1, -1):
            day = timezone.now().date() - timedelta(days=i)
            count = Ticket.objects.filter(
                organization=org,
                created_at__date=day,
            ).count()
            daily_trend.append({"day": day.strftime("%d %b"), "count": count})

        # ── Staff performance ──
        from apps.accounts.models import User, UserRole
        staff_performance = list(
            User.objects.filter(
                organization=org,
                role__in=[UserRole.STAFF, UserRole.MANAGER]
            ).annotate(
                assigned=Count(
                    "assigned_tickets",
                    filter=Q(assigned_tickets__created_at__gte=since)
                ),
                resolved=Count(
                    "assigned_tickets",
                    filter=Q(
                        assigned_tickets__created_at__gte=since,
                        assigned_tickets__status__in=[TicketStatus.CLOSED, TicketStatus.RESOLVED]
                    )
                ),
            ).filter(assigned__gt=0).order_by("-resolved")[:10]
        )

        # ── Per-location breakdown ──
        from apps.organizations.models import Location
        location_breakdown = list(
            base_qs.values("location__name")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )
        location_names = [r["location__name"] or "Unknown" for r in location_breakdown]
        location_counts = [r["count"] for r in location_breakdown]

        return render(request, "analytics/overview.html", {
            "period": period,
            "stats": {
                "total": total,
                "closed": closed,
                "resolution_rate": resolution_rate,
                "overdue": overdue,
                "avg_resolution_hours": avg_hours,
                "sla_rate": sla_rate,
                "sla_met": sla_met,
                "sla_total": sla_total,
            },
            "by_priority": json.dumps(by_priority),
            "by_status": json.dumps(by_status),
            "by_category": json.dumps(by_category),
            "daily_trend": json.dumps(daily_trend),
            "staff_performance": staff_performance,
            "by_location": json.dumps({"labels": location_names, "counts": location_counts}),
            "filter_date_from": date_from or "",
            "filter_date_to": date_to or "",
        })


class RecurringIssuesView(ManagerRequiredMixin, View):
    """
    Identify recurring issues: tickets in the same location+category
    that have appeared more than once in the last N days.
    Returns JSON suitable for a chart or table.
    """

    def get(self, request):
        org = request.org
        period = int(request.GET.get("period", 90))
        min_count = int(request.GET.get("min_count", 2))
        since = timezone.now() - timedelta(days=period)

        recurring = (
            Ticket.objects.filter(
                organization=org,
                created_at__gte=since,
                category__isnull=False,
                location__isnull=False,
            )
            .values("category__name", "location__name")
            .annotate(count=Count("id"))
            .filter(count__gte=min_count)
            .order_by("-count")[:20]
        )

        data = [
            {
                "category": r["category__name"],
                "location": r["location__name"],
                "count": r["count"],
                "label": f"{r['category__name']} @ {r['location__name']}",
            }
            for r in recurring
        ]

        return JsonResponse({"recurring_issues": data, "period_days": period})


class StatsPartialView(ManagerRequiredMixin, View):
    """HTMX partial for stat cards — responds to period selector change."""

    def get(self, request):
        org = request.org
        period = request.GET.get("period", "7")

        if period == "today":
            since = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            since = timezone.now() - timedelta(days=int(period))

        base_qs = Ticket.objects.filter(organization=org, created_at__gte=since)

        total = base_qs.count()
        closed = base_qs.filter(status__in=[TicketStatus.CLOSED, TicketStatus.RESOLVED]).count()
        open_count = base_qs.filter(status__in=["submitted", "triaged", "assigned"]).count()
        in_progress = base_qs.filter(status="in_progress").count()
        overdue = Ticket.objects.filter(
            organization=org,
            sla_resolution_due__lt=timezone.now(),
            status__in=["submitted", "triaged", "assigned", "in_progress"],
        ).count()
        critical = Ticket.objects.filter(
            organization=org,
            priority="critical",
            status__in=["submitted", "triaged", "assigned", "in_progress"],
        ).count()

        resolved_today = Ticket.objects.filter(
            organization=org,
            resolved_at__gte=timezone.now().replace(hour=0, minute=0, second=0, microsecond=0),
        ).count()

        return render(request, "analytics/partials/stat_cards.html", {
            "stats": {
                "total": total,
                "open": open_count,
                "in_progress": in_progress,
                "resolved_today": resolved_today,
                "overdue": overdue,
                "critical": critical,
            }
        })


class AnalyticsExportView(ManagerRequiredMixin, View):
    """Export analytics data as CSV download."""

    def get(self, request):
        org = request.org
        period = request.GET.get("period", "30")

        if period == "today":
            since = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            period_label = "today"
        else:
            since = timezone.now() - timedelta(days=int(period))
            period_label = f"last_{period}_days"

        tickets = Ticket.objects.filter(
            organization=org,
            created_at__gte=since,
        ).select_related("created_by", "assigned_to", "category", "location").order_by("-created_at")

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="analytics_{period_label}.csv"'

        writer = csv.writer(response)
        writer.writerow([
            "Ticket Number", "Title", "Status", "Priority", "Category",
            "Location", "Created By", "Assigned To",
            "Created At", "Resolved At", "SLA Response Due", "SLA Resolution Due",
            "SLA Response Met", "SLA Resolution Met",
        ])

        for t in tickets:
            writer.writerow([
                t.ticket_number,
                t.title,
                t.get_status_display(),
                t.get_priority_display(),
                str(t.category) if t.category else "",
                str(t.location) if t.location else "",
                t.created_by.email if t.created_by else "",
                t.assigned_to.email if t.assigned_to else "",
                t.created_at.strftime("%Y-%m-%d %H:%M") if t.created_at else "",
                t.resolved_at.strftime("%Y-%m-%d %H:%M") if t.resolved_at else "",
                t.sla_response_due.strftime("%Y-%m-%d %H:%M") if t.sla_response_due else "",
                t.sla_resolution_due.strftime("%Y-%m-%d %H:%M") if t.sla_resolution_due else "",
                "Yes" if t.sla_response_met else ("No" if t.sla_response_met is False else ""),
                "Yes" if t.sla_resolution_met else ("No" if t.sla_resolution_met is False else ""),
            ])

        return response
