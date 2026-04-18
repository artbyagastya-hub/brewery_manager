"""
Brewery Manager - Background Scheduler
Runs agent checks and scheduled tasks periodically
Includes AI planning and autonomous operations
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from models.database import Database
from utils.agent import get_agent
from utils.ai_planner import get_planner
from utils.ai_memory import get_memory

logger = logging.getLogger(__name__)

scheduler = None


def notify_staff_via_zalo(db, message: str):
    """Helper to send a Zalo message to all staff with phones"""
    try:
        staff_members = db.get_staff(active_only=True)
        count = 0
        for staff in staff_members:
            if staff.get('phone'):
                # Note: sending in 'demo' status
                db.log_zalo_message(staff['phone'], message, 'demo')
                count += 1
        if count > 0:
            logger.info(f"Zalo alert sent to {count} staff members: {message[:30]}...")
    except Exception as e:
        logger.error(f"Failed to send Zalo alert: {e}")


def start_scheduler():
    """Start the background scheduler"""
    global scheduler

    if scheduler and scheduler.running:
        logger.info("Scheduler already running")
        return scheduler

    scheduler = BackgroundScheduler()
    db = Database()
    agent = get_agent(db)

    # Run agent check every 10 minutes
    scheduler.add_job(
        func=lambda: _run_agent_check(agent, db),
        trigger=IntervalTrigger(minutes=10),
        id='agent_check',
        name='Agent Rule Check',
        replace_existing=True
    )

    # Daily revenue report at 6 PM
    scheduler.add_job(
        func=lambda: _generate_daily_report(db),
        trigger=CronTrigger(hour=18, minute=0),
        id='daily_report',
        name='Daily Revenue Report',
        replace_existing=True
    )

    # Check maintenance every hour
    scheduler.add_job(
        func=lambda: _check_maintenance(db),
        trigger=IntervalTrigger(hours=1),
        id='maintenance_check',
        name='Maintenance Check',
        replace_existing=True
    )

    # AI Planning: Generate daily agenda at 6 AM
    scheduler.add_job(
        func=lambda: _generate_daily_agenda(),
        trigger=CronTrigger(hour=6, minute=0),
        id='ai_daily_agenda',
        name='AI Daily Agenda',
        replace_existing=True
    )

    # AI Planning: Situation analysis every 30 minutes
    scheduler.add_job(
        func=lambda: _run_situation_analysis(db),
        trigger=IntervalTrigger(minutes=30),
        id='ai_situation_analysis',
        name='AI Situation Analysis',
        replace_existing=True
    )

    # AI Planning: Proactive suggestions every 2 hours
    scheduler.add_job(
        func=lambda: _check_proactive_suggestions(db),
        trigger=IntervalTrigger(hours=2),
        id='ai_proactive_check',
        name='AI Proactive Suggestions',
        replace_existing=True
    )

    scheduler.start()
    logger.info("Background scheduler started")
    return scheduler


def stop_scheduler():
    """Stop the background scheduler"""
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler stopped")


def _run_agent_check(agent, db):
    """Run agent check cycle"""
    try:
        results = agent.run_check_cycle()
        if results:
            logger.info(f"Agent triggered {len(results)} rule actions")
            notify_staff_via_zalo(db, f"🤖 Clawdbot triggered {len(results)} autonomous rule actions in the last cycle.")
    except Exception as e:
        logger.error(f"Agent check error: {e}")


def _generate_daily_report(db):
    """Generate daily revenue report"""
    try:
        from datetime import datetime
        today = datetime.now().strftime('%Y-%m-%d')
        summary = db.get_financial_summary(start_date=today, end_date=today)

        # Create notification for admins
        users = db.get_all_users()
        for user in users:
            if user.get('role') in ('admin', 'manager'):
                db.create_notification({
                    'user_id': user['id'],
                    'title': f'Daily Report - {today}',
                    'message': f"Revenue: {summary['total_income']:,.0f} VND | Expenses: {summary['total_expense']:,.0f} VND | Profit: {summary['net_profit']:,.0f} VND",
                    'type': 'info',
                    'link': '/finance'
                })

        logger.info(f"Daily report generated for {today}")
    except Exception as e:
        logger.error(f"Daily report error: {e}")


def _check_maintenance(db):
    """Check for overdue maintenance"""
    try:
        overdue = db.get_overdue_maintenance()
        if overdue:
            logger.warning(f"{len(overdue)} maintenance tasks overdue")
            notify_staff_via_zalo(db, f"⚠️ Alert: There are {len(overdue)} overdue maintenance tasks requiring attention!")
    except Exception as e:
        logger.error(f"Maintenance check error: {e}")


def _generate_daily_agenda():
    """Generate AI daily agenda"""
    try:
        planner = get_planner()
        agenda = planner.generate_daily_agenda()
        logger.info(f"Daily agenda generated: {len(agenda['tasks'])} tasks, {len(agenda['priorities'])} priorities")
    except Exception as e:
        logger.error(f"Daily agenda generation error: {e}")


def _run_situation_analysis(db):
    """Run AI situation analysis"""
    try:
        planner = get_planner()
        memory = get_memory()
        
        analysis = planner.analyze_situation()
        
        # Store alerts as observations
        critical_alerts = 0
        for alert in analysis['alerts']:
            memory.record_alert(
                alert['type'],
                alert['message'],
                alert['severity']
            )
            if alert.get('severity') in ('high', 'urgent', 'critical'):
                critical_alerts += 1
                
        if critical_alerts > 0:
            notify_staff_via_zalo(db, f"🚨 Situation Analysis identifying {critical_alerts} high-severity alert(s)! Please review dashboard.")
        
        # Update context with latest analysis
        memory.update_context('last_analysis', analysis)
        
        logger.info(f"Situation analysis: status={analysis['status']}, alerts={len(analysis['alerts'])}")
    except Exception as e:
        logger.error(f"Situation analysis error: {e}")


def _check_proactive_suggestions(db):
    """Check and create proactive notifications"""
    try:
        planner = get_planner()
        
        if planner.mode == 'reactive':
            return
        
        suggestions = planner.get_proactive_suggestions()
        
        if not suggestions:
            return
        
        # Create notifications for high-urgency suggestions
        users = db.get_all_users()
        admins = [u for u in users if u.get('role') in ('admin', 'manager')]
        
        for suggestion in suggestions:
            if suggestion['urgency'] in ('warning', 'high', 'urgent'):
                notify_staff_via_zalo(db, f"💡 AI Suggestion ({suggestion['urgency'].upper()}): {suggestion['message']}")
                for user in admins:
                    db.create_notification({
                        'user_id': user['id'],
                        'title': f"AI Suggestion: {suggestion['type'].title()}",
                        'message': suggestion['message'],
                        'type': 'suggestion',
                        'link': '/ai'
                    })
        
        logger.info(f"Proactive check: {len(suggestions)} suggestions generated")
    except Exception as e:
        logger.error(f"Proactive suggestions error: {e}")


def get_scheduler_status():
    """Get scheduler status"""
    global scheduler
    if not scheduler:
        return {'running': False, 'jobs': []}

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run': str(job.next_run_time) if job.next_run_time else None
        })

    return {
        'running': scheduler.running,
        'jobs': jobs
    }