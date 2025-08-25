import logging
import json
import os
from datetime import datetime, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import asyncio
from dotenv import load_dotenv

load_dotenv()
# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# File to store tasks
TASKS_FILE = 'tasks.json'

class TaskManager:
    def __init__(self):
        self.tasks = self.load_tasks()
    
    def load_tasks(self):
        """Load tasks from file, return empty dict if file doesn't exist"""
        if os.path.exists(TASKS_FILE):
            try:
                with open(TASKS_FILE, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}
        return {}
    
    def save_tasks(self):
        """Save tasks to file"""
        with open(TASKS_FILE, 'w') as f:
            json.dump(self.tasks, f, indent=2)
    
    def add_task(self, user_id, task, priority):
        """Add a task with priority for a user"""
        user_id = str(user_id)
        if user_id not in self.tasks:
            self.tasks[user_id] = []
        
        task_entry = {
            'task': task,
            'priority': priority,
            'added_date': datetime.now().isoformat()
        }
        self.tasks[user_id].append(task_entry)
        self.save_tasks()
    
    def get_tasks(self, user_id):
        """Get all tasks for a user"""
        user_id = str(user_id)
        return self.tasks.get(user_id, [])
    
    def remove_task(self, user_id, task_text):
        """Remove a task by matching task text"""
        user_id = str(user_id)
        if user_id in self.tasks:
            original_count = len(self.tasks[user_id])
            self.tasks[user_id] = [t for t in self.tasks[user_id] 
                                 if t['task'].lower() != task_text.lower()]
            self.save_tasks()
            return len(self.tasks[user_id]) < original_count
        return False

# Initialize task manager
task_manager = TaskManager()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    welcome_text = """
🤖 **Task Manager Bot** 

Commands:
• `/add <task>` - u got work dawg
• `/view` - evth u havent done loser
• `/done <task>` - Good boy
• `/help` - knncb got so hard meh

Im gna fkin spam u everyday so get off ur ass
Do at least 3 deliveravles a day dawg.
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message"""
    await start(update, context)

async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /add command - ask for priority"""
    if not context.args:
        await update.message.reply_text("aDD TASK! Usage: `/add <your task>`", parse_mode='Markdown')
        return
    
    task_text = ' '.join(context.args)
    
    # Store the task temporarily in user_data
    context.user_data['pending_task'] = task_text
    
    # Create priority selection buttons
    keyboard = [
        [InlineKeyboardButton("🔥 URGENT", callback_data='priority_URGENT')],
        [InlineKeyboardButton("📝 PLSDO", callback_data='priority_PLSDO')],
        [InlineKeyboardButton("😐 MEH", callback_data='priority_MEH')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Task: *{task_text}*\n\nSelect priority:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    #create due dates for each task / no due date 
    
    

async def priority_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle priority selection callback"""
    query = update.callback_query
    await query.answer()
    
    # Extract priority from callback data
    priority = query.data.replace('priority_', '')
    task_text = context.user_data.get('pending_task')
    
    if not task_text:
        await query.edit_message_text("Error: No pending task found. Please try adding the task again.")
        return
    
    # Add task to the list
    user_id = query.from_user.id
    task_manager.add_task(user_id, task_text, priority)
    
    # Clear pending task
    context.user_data.pop('pending_task', None)
    
    priority_emoji = {'URGENT': '🔥', 'PLSDO': '📝', 'MEH': '😐'}
    
    await query.edit_message_text(
        f"✅ Task added! u btr rmb this \n\n*{task_text}*\nPriority: {priority_emoji.get(priority, '')} {priority}"
    , parse_mode='Markdown')

async def view_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display all tasks for the user"""
    user_id = update.effective_user.id
    tasks = task_manager.get_tasks(user_id)
    
    if not tasks:
        await update.message.reply_text("📝 No way u dh anth to do. Use `/add <task>` to add your first task.", parse_mode='Markdown')
        return
    
    # Sort tasks by priority
    priority_order = {'URGENT': 0, 'PLSDO': 1, 'MEH': 2}
    tasks.sort(key=lambda x: priority_order.get(x['priority'], 3))
    
    priority_emoji = {'URGENT': '🔥', 'PLSDO': '📝', 'MEH': '😐'}
    
    message = "📋 **Your Tasks:**\n\n"
    
    for i, task in enumerate(tasks, 1):
        emoji = priority_emoji.get(task['priority'], '')
        date_added = datetime.fromisoformat(task['added_date']).strftime('%m/%d')
        message += f"{i}. {emoji} *{task['task']}* ({task['priority']}) - Added {date_added}\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def done_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mark a task as done (remove it)"""
    if not context.args:
        await update.message.reply_text("Please specify which task to mark as done! Usage: `/done <task>`", parse_mode='Markdown')
        return
    
    task_text = ' '.join(context.args)
    user_id = update.effective_user.id
    
    if task_manager.remove_task(user_id, task_text):
        await update.message.reply_text(f"✅ Good boy!!: *{task_text}*", parse_mode='Markdown')
    else:
        await update.message.reply_text(f"❌ Task not found: *{task_text}*\n\nUse `/view` to see your current tasks.", parse_mode='Markdown')

async def send_daily_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Send daily reminders to all users with tasks"""
    for user_id, tasks in task_manager.tasks.items():
        if tasks:  # Only send if user has tasks
            try:
                # Sort by priority
                priority_order = {'URGENT': 0, 'PLSDO': 1, 'MEH': 2}
                tasks.sort(key=lambda x: priority_order.get(x['priority'], 3))
                
                priority_emoji = {'URGENT': '🔥', 'PLSDO': '📝', 'MEH': '😐'}
                
                message = "⏰ **Daily Task Reminder**\n\n"
                
                for i, task in enumerate(tasks, 1):
                    emoji = priority_emoji.get(task['priority'], '')
                    message += f"{i}. {emoji} {task['task']} ({task['priority']})\n"
                
                message += f"\n📝 You have {len(tasks)} pending tasks. GET OFF UR ASS DAWG"
                
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text=message,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to send reminder to user {user_id}: {e}")

def main():
    """Start the bot"""
    # Replace 'YOUR_BOT_TOKEN' with your actual bot token
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add", add_task))
    application.add_handler(CommandHandler("view", view_tasks))
    application.add_handler(CommandHandler("done", done_task))
    
    # Add callback query handler for priority buttons
    application.add_handler(CallbackQueryHandler(priority_callback, pattern='^priority_'))
    
    # Schedule daily reminders (12 AM every day)
    job_queue = application.job_queue
    job_queue.run_daily(send_daily_reminder, time=time(hour=0, minute=0))
    
    # Run the bot
    print("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()