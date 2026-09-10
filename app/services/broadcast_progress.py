def format_progress_text(job: dict) -> str:
    job_id = job.get("job_id", "")
    status = job.get("status", "pending")
    total = int(job.get("total") or 0)
    sent = int(job.get("sent") or 0)
    failed = int(job.get("failed") or 0)
    done = sent + failed
    pct = int((done / total) * 100) if total else 0
    bar_filled = min(10, pct // 10)
    bar = "█" * bar_filled + "░" * (10 - bar_filled)

    status_labels = {
        "pending": "Preparing recipients…",
        "running": "Sending…",
        "completed": "✅ Completed",
        "cancelled": "⏹ Stopped",
        "failed": "❌ Failed",
    }
    label = status_labels.get(status, status)

    lines = [
        f"📢 <b>Broadcast</b> <code>{job_id[:8]}</code>",
        f"{label}",
        f"<code>{bar}</code> {pct}%",
        f"Sent: <b>{sent}</b> · Failed: <b>{failed}</b> · Total: <b>{total}</b>",
    ]
    if status in ("completed", "cancelled", "failed"):
        lines.append("\n<i>This job is finished.</i>")
    return "\n".join(lines)
