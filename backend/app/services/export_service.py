"""
Export Service

Handles exporting content in multiple formats (JSON, Markdown, PDF).
"""

import json
import io
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum


class ExportFormat(str, Enum):
    """Export format options."""
    JSON = "json"
    MARKDOWN = "markdown"
    PDF = "pdf"
    CSV = "csv"


class ExportService:
    """Service for exporting data in various formats."""

    def __init__(self):
        """Initialize export service."""
        pass

    async def export_session(
        self,
        session_data: Dict[str, Any],
        format: ExportFormat,
        include_messages: bool = True,
        include_evaluation: bool = True,
    ) -> bytes:
        """
        Export session data in specified format.

        Args:
            session_data: Session data to export
            format: Export format
            include_messages: Include conversation messages
            include_evaluation: Include evaluation data

        Returns:
            Exported data as bytes
        """
        if format == ExportFormat.JSON:
            return self._export_json(session_data)
        elif format == ExportFormat.MARKDOWN:
            return self._export_markdown(session_data, include_messages, include_evaluation)
        elif format == ExportFormat.PDF:
            return await self._export_pdf(session_data, include_messages, include_evaluation)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    async def export_project(
        self,
        project_data: Dict[str, Any],
        format: ExportFormat,
        include_sessions: bool = True,
    ) -> bytes:
        """
        Export project data in specified format.

        Args:
            project_data: Project data to export
            format: Export format
            include_sessions: Include session data

        Returns:
            Exported data as bytes
        """
        if format == ExportFormat.JSON:
            return self._export_json(project_data)
        elif format == ExportFormat.MARKDOWN:
            return self._export_project_markdown(project_data, include_sessions)
        elif format == ExportFormat.PDF:
            return await self._export_project_pdf(project_data, include_sessions)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    async def export_analytics(
        self,
        analytics_data: Dict[str, Any],
        format: ExportFormat,
    ) -> bytes:
        """
        Export analytics data in specified format.

        Args:
            analytics_data: Analytics data to export
            format: Export format

        Returns:
            Exported data as bytes
        """
        if format == ExportFormat.JSON:
            return self._export_json(analytics_data)
        elif format == ExportFormat.CSV:
            return self._export_csv(analytics_data)
        elif format == ExportFormat.MARKDOWN:
            return self._export_analytics_markdown(analytics_data)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _export_json(self, data: Dict[str, Any]) -> bytes:
        """Export data as JSON."""
        json_str = json.dumps(data, indent=2, default=str, ensure_ascii=False)
        return json_str.encode('utf-8')

    def _export_markdown(
        self,
        session_data: Dict[str, Any],
        include_messages: bool,
        include_evaluation: bool,
    ) -> bytes:
        """Export session data as Markdown."""
        lines = []

        # Header
        lines.append(f"# Session Report: {session_data.get('id', 'N/A')}")
        lines.append("")
        lines.append(f"**Date:** {session_data.get('started_at', 'N/A')}")
        lines.append(f"**Status:** {session_data.get('status', 'N/A')}")
        lines.append(f"**Duration:** {session_data.get('duration_seconds', 0)} seconds")
        lines.append("")

        # Session Info
        lines.append("## Session Information")
        lines.append("")
        lines.append(f"- **User ID:** {session_data.get('user_id', 'N/A')}")
        lines.append(f"- **Task ID:** {session_data.get('task_id', 'N/A')}")
        lines.append(f"- **Score:** {session_data.get('score', 'N/A')}")
        lines.append(f"- **Turns:** {session_data.get('turns_count', 0)}")
        lines.append("")

        # Sales Metrics
        if 'sales_state' in session_data:
            lines.append("## Sales Metrics")
            lines.append("")
            lines.append(f"- **Sales State:** {session_data.get('sales_state', 'N/A')}")
            lines.append(f"- **Customer Interest:** {session_data.get('customer_interest', 0):.2f}")
            lines.append(f"- **Objections Raised:** {session_data.get('objections_raised', 0)}")
            lines.append(f"- **Objections Resolved:** {session_data.get('objections_resolved', 0)}")
            lines.append("")

        # Messages
        if include_messages and 'messages' in session_data:
            lines.append("## Conversation")
            lines.append("")
            for msg in session_data['messages']:
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                timestamp = msg.get('created_at', '')
                lines.append(f"### {role.upper()} ({timestamp})")
                lines.append("")
                lines.append(content)
                lines.append("")

        # Evaluation
        if include_evaluation and 'evaluation' in session_data:
            eval_data = session_data['evaluation']
            lines.append("## Evaluation")
            lines.append("")
            lines.append(f"**Overall Score:** {eval_data.get('overall_score', 'N/A')}/10")
            lines.append("")

            if 'strengths' in eval_data:
                lines.append("### Strengths")
                lines.append("")
                for strength in eval_data['strengths']:
                    lines.append(f"- {strength}")
                lines.append("")

            if 'weaknesses' in eval_data:
                lines.append("### Areas for Improvement")
                lines.append("")
                for weakness in eval_data['weaknesses']:
                    lines.append(f"- {weakness}")
                lines.append("")

            if 'suggestions' in eval_data:
                lines.append("### Suggestions")
                lines.append("")
                for suggestion in eval_data['suggestions']:
                    lines.append(f"- {suggestion}")
                lines.append("")

        markdown_content = "\n".join(lines)
        return markdown_content.encode('utf-8')

    def _export_project_markdown(
        self,
        project_data: Dict[str, Any],
        include_sessions: bool,
    ) -> bytes:
        """Export project data as Markdown."""
        lines = []

        # Header
        lines.append(f"# Project Report: {project_data.get('name', 'N/A')}")
        lines.append("")
        lines.append(f"**Created:** {project_data.get('created_at', 'N/A')}")
        lines.append(f"**Status:** {project_data.get('status', 'N/A')}")
        lines.append("")

        # Description
        lines.append("## Description")
        lines.append("")
        lines.append(project_data.get('description', 'No description'))
        lines.append("")

        # Statistics
        lines.append("## Statistics")
        lines.append("")
        lines.append(f"- **Total Tasks:** {project_data.get('tasks_count', 0)}")
        lines.append(f"- **Completed Tasks:** {project_data.get('completed_tasks', 0)}")
        lines.append(f"- **Completion Rate:** {project_data.get('completion_rate', 0):.1f}%")
        lines.append(f"- **Total Sessions:** {project_data.get('total_sessions', 0)}")
        lines.append(f"- **Average Score:** {project_data.get('avg_score', 0):.1f}")
        lines.append("")

        # Sessions
        if include_sessions and 'sessions' in project_data:
            lines.append("## Sessions")
            lines.append("")
            for session in project_data['sessions']:
                lines.append(f"### Session {session.get('id', 'N/A')}")
                lines.append("")
                lines.append(f"- **Date:** {session.get('started_at', 'N/A')}")
                lines.append(f"- **Score:** {session.get('score', 'N/A')}")
                lines.append(f"- **Status:** {session.get('status', 'N/A')}")
                lines.append("")

        markdown_content = "\n".join(lines)
        return markdown_content.encode('utf-8')

    def _export_analytics_markdown(self, analytics_data: Dict[str, Any]) -> bytes:
        """Export analytics data as Markdown."""
        lines = []

        lines.append("# Analytics Report")
        lines.append("")
        lines.append(f"**Generated:** {datetime.now().isoformat()}")
        lines.append("")

        # Overview
        if 'overview' in analytics_data:
            overview = analytics_data['overview']
            lines.append("## Overview")
            lines.append("")
            for key, value in overview.items():
                lines.append(f"- **{key.replace('_', ' ').title()}:** {value}")
            lines.append("")

        # Performance Metrics
        if 'metrics' in analytics_data:
            lines.append("## Performance Metrics")
            lines.append("")
            for metric_name, metric_value in analytics_data['metrics'].items():
                lines.append(f"### {metric_name.replace('_', ' ').title()}")
                lines.append("")
                if isinstance(metric_value, dict):
                    for k, v in metric_value.items():
                        lines.append(f"- **{k}:** {v}")
                else:
                    lines.append(f"- {metric_value}")
                lines.append("")

        markdown_content = "\n".join(lines)
        return markdown_content.encode('utf-8')

    async def _export_pdf(
        self,
        session_data: Dict[str, Any],
        include_messages: bool,
        include_evaluation: bool,
    ) -> bytes:
        """Export session data as PDF."""
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib import colors
        except ImportError:
            # Fallback to markdown if reportlab not available
            return self._export_markdown(session_data, include_messages, include_evaluation)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a202c'),
        )
        story.append(Paragraph(f"Session Report: {session_data.get('id', 'N/A')}", title_style))
        story.append(Spacer(1, 0.3 * inch))

        # Session Info
        info_data = [
            ['Date:', session_data.get('started_at', 'N/A')],
            ['Status:', session_data.get('status', 'N/A')],
            ['Duration:', f"{session_data.get('duration_seconds', 0)} seconds"],
            ['Score:', str(session_data.get('score', 'N/A'))],
        ]

        info_table = Table(info_data, colWidths=[2 * inch, 4 * inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        story.append(info_table)
        story.append(Spacer(1, 0.3 * inch))

        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.read()

    async def _export_project_pdf(
        self,
        project_data: Dict[str, Any],
        include_sessions: bool,
    ) -> bytes:
        """Export project data as PDF."""
        # Fallback to markdown
        return self._export_project_markdown(project_data, include_sessions)

    def _export_csv(self, analytics_data: Dict[str, Any]) -> bytes:
        """Export analytics data as CSV."""
        import csv

        buffer = io.StringIO()

        if 'metrics' in analytics_data and isinstance(analytics_data['metrics'], list):
            if len(analytics_data['metrics']) > 0:
                fieldnames = analytics_data['metrics'][0].keys()
                writer = csv.DictWriter(buffer, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(analytics_data['metrics'])
        else:
            # Simple key-value export
            writer = csv.writer(buffer)
            writer.writerow(['Metric', 'Value'])
            for key, value in analytics_data.items():
                if not isinstance(value, (dict, list)):
                    writer.writerow([key, value])

        csv_content = buffer.getvalue()
        return csv_content.encode('utf-8')


# Global export service instance
export_service = ExportService()
