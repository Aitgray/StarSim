from src.starsim.core.log import AuditLog

def generate_gazette(log: AuditLog, tick: int) -> str:
    """Generates a simple text summary of the events in a tick."""
    report = f"== Tick {tick} Report ==\n"
    
    tick_entries = [entry for entry in log.entries if entry.tick == tick]

    if not tick_entries:
        report += "No significant events occurred.\n"
        return report

    for entry in tick_entries:
        report += f"- [{entry.type}] {entry.reason}\n"
        if entry.details:
            report += f"  Details: {entry.details}\n"
            
    return report
