from dotenv import load_dotenv
load_dotenv()

import asyncio
import io
import logging
import uuid
from datetime import datetime
from typing import Optional, List, Dict
import chainlit as cl
from openai import OpenAI
import os

# Import our custom modules
from database import ChatDatabase
from config import config, validate_file_upload, format_file_size, truncate_text

# Configure logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=config.openai_api_key)

class RAGAssistant:
    """OpenAI RAG Assistant with vector store management."""
    
    def __init__(self, organization_name: str):
        self.organization_name = organization_name
        self.db = ChatDatabase(organization_name)
        self.vector_store_id = None
        self.assistant_id = None
    
    async def get_or_create_vector_store(self) -> str:
        """Get existing vector store or create a new one."""
        # Check database for existing vector store
        vector_store_id = self.db.get_vector_store()
        
        if vector_store_id:
            try:
                # Verify it still exists in OpenAI
                vector_store = client.vector_stores.retrieve(vector_store_id)
                logger.info(f"Using existing vector store: {vector_store_id}")
                return vector_store_id
            except Exception as e:
                logger.warning(f"Vector store {vector_store_id} not found in OpenAI, creating new one: {e}")
        
        # Create new vector store
        vector_store = client.vector_stores.create(
            name=config.vector_store_name,
            expires_after={
                "anchor": "last_active_at",
                "days": config.vector_store_expires_days
            }
        )
        
        # Save to database
        self.db.create_vector_store(vector_store.id, config.vector_store_name)
        logger.info(f"Created new vector store: {vector_store.id}")
        
        return vector_store.id
    
    async def create_assistant(self, vector_store_id: str) -> str:
        """Create an OpenAI assistant with file search capability."""
        assistant = client.beta.assistants.create(
            name=f"{config.organization_display_name} RAG Assistant",
            instructions=config.assistant_instructions,
            model=config.openai_assistant_model,
            tools=[{"type": "file_search"}],
            tool_resources={
                "file_search": {
                    "vector_store_ids": [vector_store_id]
                }
            }
        )
        
        logger.info(f"Created assistant: {assistant.id}")
        return assistant.id
    
    async def upload_documents(self, files: List[cl.File], user_id: str = None) -> Dict:
        """Upload documents to the vector store."""
        if not files:
            return {"success": False, "message": "No files provided"}
        
        vector_store_id = await self.get_or_create_vector_store()
        
        uploaded_files = []
        errors = []
        
        for file in files:
            try:
                # Handle Chainlit File elements that have .path instead of .content
                file_content = None
                file_name = getattr(file, 'name', 'unknown_file')
                
                if hasattr(file, 'content') and file.content is not None:
                    # File has direct content
                    file_content = file.content
                elif hasattr(file, 'path') and file.path:
                    # File has path, read content from disk
                    import os
                    file_name = os.path.basename(file.path)
                    with open(file.path, 'rb') as f:
                        file_content = f.read()
                else:
                    errors.append(f"{file_name}: No file content or path available")
                    continue
                
                # Check if file content is valid
                if file_content is None or len(file_content) == 0:
                    errors.append(f"{file_name}: File content is empty or corrupted")
                    continue
                    
                # Validate file
                is_valid, validation_message = validate_file_upload(file_name, len(file_content))
                if not is_valid:
                    errors.append(f"{file_name}: {validation_message}")
                    continue
                
                # Create file stream for OpenAI
                file_stream = io.BytesIO(file_content)
                file_stream.name = file_name
                
                # Upload to OpenAI
                openai_file = client.files.create(
                    file=file_stream,
                    purpose="assistants"
                )
                
                # Add to vector store
                client.vector_stores.files.create_and_poll(
                    vector_store_id=vector_store_id,
                    file_id=openai_file.id
                )
                
                # Save to database
                self.db.add_document(
                    filename=file_name,
                    openai_file_id=openai_file.id,
                    vector_store_id=vector_store_id,
                    file_size=len(file_content),
                    uploaded_by=user_id
                )
                
                uploaded_files.append({
                    'filename': file_name,
                    'id': openai_file.id,
                    'size': len(file_content)
                })
                
                logger.info(f"Uploaded document: {file_name} ({openai_file.id})")
                
            except Exception as e:
                error_msg = f"{file_name}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"Error uploading {file_name}: {e}")
                # Add debug info about the error
                import traceback
                logger.error(f"Full traceback for {file_name}:\n{traceback.format_exc()}")
        
        return {
            "success": len(uploaded_files) > 0,
            "uploaded_files": uploaded_files,
            "errors": errors,
            "total_files": len(files),
            "successful_uploads": len(uploaded_files)
        }
    
    async def delete_document(self, file_id: str) -> bool:
        """Delete a document from OpenAI and mark as deleted in database."""
        try:
            # Delete from OpenAI
            client.files.delete(file_id)
            
            # Mark as deleted in database
            self.db.delete_document(file_id)
            
            logger.info(f"Deleted document: {file_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting document {file_id}: {e}")
            return False

# Global RAG assistant instance
rag_assistant = RAGAssistant(config.organization_name)

@cl.on_chat_start
async def start():
    """Initialize chat session."""
    try:
        # Get user information
        user = cl.user_session.get("user")
        user_id = None
        user_name = "Anonymous"
        
        if user:
            user_id = getattr(user, "identifier", None) or getattr(user, "email", None) or str(uuid.uuid4())
            user_name = getattr(user, "name", None) or getattr(user, "email", None) or "User"
            
            # Update user in database
            rag_assistant.db.create_or_update_user(
                user_id=user_id,
                email=getattr(user, "email", None),
                name=user_name
            )
        else:
            user_id = str(uuid.uuid4())
        
        # Create chat session
        session_id = str(uuid.uuid4())
        
        # Get or create vector store and assistant
        vector_store_id = await rag_assistant.get_or_create_vector_store()
        assistant_id = await rag_assistant.create_assistant(vector_store_id)
        
        # Create OpenAI thread
        thread = client.beta.threads.create()
        
        # Save session to database
        rag_assistant.db.create_chat_session(
            session_id=session_id,
            user_id=user_id,
            thread_id=thread.id,
            assistant_id=assistant_id,
            vector_store_id=vector_store_id
        )
        
        # Store in session
        cl.user_session.set("session_id", session_id)
        cl.user_session.set("user_id", user_id)
        cl.user_session.set("thread_id", thread.id)
        cl.user_session.set("assistant_id", assistant_id)
        cl.user_session.set("vector_store_id", vector_store_id)
        
        # Get current document count
        doc_count = rag_assistant.db.get_document_count()
        
        welcome_message = f"Welcome to **{config.organization_display_name}** RAG Assistant! 👋\n\n"
        welcome_message += f"📚 **Knowledge Base**: {doc_count} document(s) available\n\n"
        welcome_message += "**How to use:**\n"
        welcome_message += "• 💬 Ask questions about your documents\n"
        welcome_message += "• 📎 Upload files by dragging them into this chat\n"
        welcome_message += "• 🔍 I'll automatically search your knowledge base for relevant information\n\n"
        welcome_message += "*What would you like to know about your documents?*"
        
        await cl.Message(content=welcome_message).send()
        
        # Add knowledge base management commands info
        if doc_count == 0:
            kb_tip = cl.Message(
                content="💡 **Quick Tip**: Type `/kb` to see knowledge base commands or simply drag files here to upload!"
            )
            await kb_tip.send()
        
        logger.info(f"Started chat session {session_id} for user {user_name}")
        
    except Exception as e:
        logger.error(f"Error in chat start: {e}")
        await cl.Message(content="❌ Error initializing chat. Please refresh and try again.").send()

async def handle_slash_commands(message: cl.Message):
    """Handle knowledge base commands and regular messages."""
    content = message.content.strip()
    
    # Handle slash commands for knowledge base
    if content.startswith('/kb'):
        await handle_knowledge_base_command(content)
        return True
    elif content.startswith('/docs'):
        await handle_documents_command()
        return True
    elif content.startswith('/help'):
        await handle_help_command()
        return True
    
    return False

async def handle_knowledge_base_command(command: str):
    """Handle knowledge base slash commands."""
    try:
        user_id = cl.user_session.get("user_id")
        
        if command == '/kb' or command == '/kb list':
            # List all documents
            documents = rag_assistant.db.list_documents()
            
            if not documents:
                content = "## 📚 Knowledge Base\n\n**No documents found.**\n\nUpload documents by dragging them into the chat!"
            else:
                content = "## 📚 Knowledge Base\n\n**Your Documents:**\n\n"
                for i, doc in enumerate(documents, 1):
                    upload_date = doc.get('upload_date', 'Unknown')
                    file_size = format_file_size(doc.get('file_size', 0))
                    content += f"{i}. **{doc['filename']}** ({file_size})\n   📅 Uploaded: {upload_date}\n\n"
                
                content += f"**Total: {len(documents)} documents**\n\n"
                content += "💡 *Commands: `/kb list`, `/docs`, `/help`*"
            
            await cl.Message(content=content).send()
            
        elif command.startswith('/kb search '):
            search_term = command[11:].strip()
            if search_term:
                await cl.Message(content=f"🔍 Searching for: **{search_term}**\n\nLet me find relevant information in your documents...").send()
                # This will be handled by the regular message processing
                await handle_message_content(cl.Message(content=f"Find information about: {search_term}"))
            else:
                await cl.Message(content="❌ Please provide a search term: `/kb search your query`").send()
        else:
            await cl.Message(content="❌ Unknown command. Use `/help` for available commands.").send()
            
    except Exception as e:
        logger.error(f"Error in knowledge base command: {e}")
        await cl.Message(content="❌ Error processing knowledge base command.").send()

async def handle_documents_command():
    """Show document statistics and management options."""
    try:
        user_id = cl.user_session.get("user_id")
        
        # Get document statistics
        total_docs = rag_assistant.db.get_document_count()
        user_docs = rag_assistant.db.list_documents()
        
        content = "## 📊 Document Statistics\n\n"
        content += f"📚 **Total Documents**: {total_docs}\n"
        content += f"👤 **Your Documents**: {len(user_docs)}\n\n"
        
        # Recent uploads
        if user_docs:
            content += "**Recent Uploads:**\n"
            for doc in user_docs[:3]:  # Show last 3
                content += f"• {doc['filename']}\n"
            
            if len(user_docs) > 3:
                content += f"• ... and {len(user_docs) - 3} more\n"
        
        content += "\n💡 *Use `/kb list` to see all documents*"
        
        await cl.Message(content=content).send()
        
    except Exception as e:
        logger.error(f"Error in documents command: {e}")
        await cl.Message(content="❌ Error loading document statistics.").send()

async def handle_help_command():
    """Show help information."""
    content = """## 🆘 Help & Commands

**Slash Commands:**
• `/kb` or `/kb list` - View all documents in knowledge base
• `/kb search <query>` - Search through your documents  
• `/docs` - Show document statistics
• `/help` - Show this help message

**File Upload:**
• Drag & drop files directly into the chat
• Supported: PDF, DOCX, TXT, MD, HTML, JSON, CSV, XML
• Max file size: 20MB per file

**Chat Features:**
• Ask questions about your uploaded documents
• Follow-up questions maintain conversation context
• Streaming responses for real-time interaction

**Examples:**
• "What are the main topics in my documents?"
• "Summarize the key points from the uploaded PDFs"
• "Find information about [specific topic]"

💡 *Just start typing your question - I'll automatically search your knowledge base!*"""
    
    await cl.Message(content=content).send()

# Message handler will be defined later to combine with file upload handling

@cl.on_message
async def upload_files_handler(message: cl.Message):
    """Handle file uploads in messages"""
    # Check for slash commands first
    if await handle_slash_commands(message):
        return
    
    # Check if message has files attached
    if not message.elements:
        # Regular message handling
        await handle_message_content(message)
        return
    
    # Handle file uploads
    try:
        user_id = cl.user_session.get("user_id")
        
        # Show upload progress
        progress_msg = cl.Message(content="🔄 Uploading documents...")
        await progress_msg.send()
        
        # Convert elements to files format
        file_elements = []
        for element in message.elements:
            if hasattr(element, 'path'):
                file_elements.append(element)
        
        if not file_elements:
            progress_msg.content = "❌ No valid files found."
            await progress_msg.update()
            return
        
        # Upload documents
        result = await rag_assistant.upload_documents(file_elements, user_id)
        
        if result["success"]:
            # Create success message
            success_content = f"✅ Successfully uploaded {result['successful_uploads']} out of {result['total_files']} documents:\n\n"
            
            for doc in result["uploaded_files"]:
                size_str = format_file_size(doc['size'])
                success_content += f"• **{doc['filename']}** ({size_str})\n"
            
            if result["errors"]:
                success_content += f"\n⚠️ **Errors:**\n"
                for error in result["errors"]:
                    success_content += f"• {error}\n"
            
            progress_msg.content = success_content
            await progress_msg.update()
        else:
            error_content = "❌ Upload failed:\n\n"
            for error in result["errors"]:
                error_content += f"• {error}\n"
            progress_msg.content = error_content
            await progress_msg.update()
        
    except Exception as e:
        logger.error(f"Error in file upload: {e}")
        await cl.Message(content=f"❌ Error uploading files: {str(e)}").send()

@cl.action_callback("knowledge_base")
async def handle_knowledge_base_action(action):
    """Handle knowledge base page navigation."""
    try:
        user_id = cl.user_session.get("user_id")
        
        # Get all documents for this user/organization
        documents = rag_assistant.db.list_documents()
        
        if not documents:
            content = "## 📁 Knowledge Base\n\n**No documents found.**\n\nUpload documents by dragging them into the chat or using the file upload feature."
        else:
            content = "## 📁 Knowledge Base\n\n**Your Documents:**\n\n"
            for doc in documents:
                upload_date = doc.get('upload_date', 'Unknown')
                file_size = format_file_size(doc.get('file_size', 0))
                content += f"• **{doc['filename']}** ({file_size}) - Uploaded: {upload_date}\n"
            
            content += f"\n**Total: {len(documents)} documents**\n\n"
            content += "💡 *Tip: Ask me questions about these documents and I'll search through them for relevant information.*"
        
        await cl.Message(content=content).send()
        
    except Exception as e:
        logger.error(f"Error in knowledge base action: {e}")
        await cl.Message(content="❌ Error loading knowledge base.").send()

@cl.action_callback("chat_history")
async def handle_chat_history_action(action):
    """Handle chat history page navigation."""
    try:
        user_id = cl.user_session.get("user_id")
        
        # Get recent chat sessions
        sessions = rag_assistant.db.get_user_sessions(user_id, limit=10) if user_id else []
        
        if not sessions:
            content = "## 💬 Chat History\n\n**No previous conversations found.**\n\nYour chat history will appear here as you have conversations."
        else:
            content = "## 💬 Chat History\n\n**Recent Conversations:**\n\n"
            for session in sessions:
                title = session.get('title', 'Untitled Chat')[:50]
                last_activity = session.get('last_activity', 'Unknown')
                message_count = session.get('message_count', 0)
                content += f"• **{title}** ({message_count} messages) - {last_activity}\n"
            
            content += f"\n**Total: {len(sessions)} conversations**"
        
        await cl.Message(content=content).send()
        
    except Exception as e:
        logger.error(f"Error in chat history action: {e}")
        await cl.Message(content="❌ Error loading chat history.").send()

async def handle_message_content(message: cl.Message):
    """Handle regular text messages."""
    try:
        # Get session data
        session_id = cl.user_session.get("session_id")
        user_id = cl.user_session.get("user_id")
        thread_id = cl.user_session.get("thread_id")
        assistant_id = cl.user_session.get("assistant_id")
        
        if not all([session_id, thread_id, assistant_id]):
            await cl.Message("❌ Session error. Please refresh the page.").send()
            return
        
        # Save user message to database
        rag_assistant.db.save_message(session_id, "user", message.content)
        
        # Add message to OpenAI thread
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message.content
        )
        
        # Create response message
        response_msg = cl.Message(content="")
        await response_msg.send()
        
        # Stream the response
        response_content = ""
        with client.beta.threads.runs.stream(
            thread_id=thread_id,
            assistant_id=assistant_id
        ) as stream:
            for text in stream.text_deltas:
                response_content += text
                await response_msg.stream_token(text)
        
        await response_msg.update()
        
        # Save assistant response to database
        rag_assistant.db.save_message(session_id, "assistant", response_content)
        
        # Update session activity
        rag_assistant.db.update_session_activity(session_id)
        
        # Auto-generate chat title if this is the first exchange
        message_count = rag_assistant.db.get_message_count(session_id)
        if message_count == 2:  # First user message + first assistant response
            title = truncate_text(message.content, config.chat_title_length)
            rag_assistant.db.update_chat_title(session_id, title)
        
    except Exception as e:
        logger.error(f"Error in message handling: {e}")
        await cl.Message(content="❌ Error processing message. Please try again.").send()

# Action handlers
@cl.action_callback("view_docs")
async def view_documents():
    """Display uploaded documents."""
    try:
        docs = rag_assistant.db.list_documents()
        
        if not docs:
            await cl.Message(content="📄 No documents uploaded yet.").send()
            return
        
        # Create formatted document list
        doc_content = f"📚 **Knowledge Base ({len(docs)} documents):**\n\n"
        
        for i, doc in enumerate(docs, 1):
            size_str = format_file_size(doc['size'])
            doc_content += f"{i}. **{doc['filename']}**\n"
            doc_content += f"   • Size: {size_str}\n"
            doc_content += f"   • Uploaded: {doc['upload_date']}\n"
            doc_content += f"   • By: {doc['uploaded_by']}\n"
            doc_content += f"   • ID: `{doc['id'][:16]}...`\n\n"
        
        # Add delete actions
        delete_actions = []
        for doc in docs[:10]:  # Limit to 10 for UI purposes
            delete_actions.append(
                cl.Action(
                    name="delete_doc",
                    value=doc['id'],
                    label=f"🗑️ Delete {truncate_text(doc['filename'], 20)}"
                )
            )
        
        await cl.Message(
            content=doc_content,
            actions=delete_actions
        ).send()
        
    except Exception as e:
        logger.error(f"Error viewing documents: {e}")
        await cl.Message(content="❌ Error loading documents.").send()

@cl.action_callback("view_chats")
async def view_chat_history():
    """Display chat history."""
    try:
        user_id = cl.user_session.get("user_id")
        sessions = rag_assistant.db.list_chat_sessions(user_id, limit=20)
        
        if not sessions:
            await cl.Message(content="💬 No previous chats found.").send()
            return
        
        chat_content = f"💬 **Recent Conversations ({len(sessions)}):**\n\n"
        
        for i, session in enumerate(sessions, 1):
            chat_content += f"{i}. **{session['title']}**\n"
            chat_content += f"   • Started: {session['created_at']}\n"
            chat_content += f"   • Messages: {session['message_count']}\n"
            chat_content += f"   • Last active: {session['last_activity']}\n\n"
        
        await cl.Message(content=chat_content).send()
        
    except Exception as e:
        logger.error(f"Error viewing chat history: {e}")
        await cl.Message(content="❌ Error loading chat history.").send()

@cl.action_callback("stats")
async def view_stats():
    """Display system statistics."""
    try:
        stats = rag_assistant.db.get_stats()
        
        stats_content = f"📊 **{config.organization_display_name} Statistics:**\n\n"
        stats_content += f"📄 **Documents:** {stats['documents']}\n"
        stats_content += f"💬 **Chat Sessions:** {stats['sessions']}\n"
        stats_content += f"📝 **Total Messages:** {stats['messages']}\n"
        stats_content += f"👥 **Users:** {stats['users']}\n"
        stats_content += f"🕐 **Messages (24h):** {stats['messages_24h']}\n\n"
        stats_content += f"🏢 **Organization:** {stats['organization']}\n"
        stats_content += f"🤖 **Model:** {config.openai_assistant_model}\n"
        stats_content += f"📁 **Max File Size:** {config.max_file_size_mb}MB\n"
        
        await cl.Message(content=stats_content).send()
        
    except Exception as e:
        logger.error(f"Error viewing stats: {e}")
        await cl.Message(content="❌ Error loading statistics.").send()

@cl.action_callback("delete_doc")
async def delete_document_action(action):
    """Handle document deletion."""
    try:
        file_id = action.value
        
        # Find document name for confirmation
        docs = rag_assistant.db.list_documents()
        doc_name = next((d['filename'] for d in docs if d['id'] == file_id), "Unknown")
        
        # Ask for confirmation
        confirm_actions = [
            cl.Action(name="confirm_delete", value=file_id, label="✅ Yes, Delete"),
            cl.Action(name="cancel_delete", value="cancel", label="❌ Cancel")
        ]
        
        await cl.Message(
            content=f"⚠️ Are you sure you want to delete **{doc_name}**?\n\nThis action cannot be undone.",
            actions=confirm_actions
        ).send()
        
    except Exception as e:
        logger.error(f"Error in delete document action: {e}")
        await cl.Message(content="❌ Error processing delete request.").send()

@cl.action_callback("confirm_delete")
async def confirm_delete_document(action):
    """Confirm and execute document deletion."""
    try:
        file_id = action.value
        
        # Get document name before deletion
        docs = rag_assistant.db.list_documents()
        doc_name = next((d['filename'] for d in docs if d['id'] == file_id), "Unknown")
        
        # Delete the document
        success = await rag_assistant.delete_document(file_id)
        
        if success:
            await cl.Message(content=f"✅ Successfully deleted **{doc_name}**").send()
        else:
            await cl.Message(content=f"❌ Failed to delete **{doc_name}**").send()
        
    except Exception as e:
        logger.error(f"Error confirming delete: {e}")
        await cl.Message(content="❌ Error deleting document.").send()

@cl.action_callback("cancel_delete")
async def cancel_delete_document(action):
    """Cancel document deletion."""
    await cl.Message(content="❌ Document deletion cancelled.").send()

# Health check endpoint for Cloud Run
@cl.server.app.get("/health")
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    try:
        # Basic health checks
        health_status = {
            "status": "healthy",
            "organization": config.organization_name,
            "database": "connected",
            "openai": "configured" if config.openai_api_key else "missing",
            "timestamp": datetime.now().isoformat()
        }
        
        # Test database connection
        try:
            stats = rag_assistant.db.get_stats()
            health_status["database"] = "operational"
            health_status["documents"] = stats["documents"]
            health_status["sessions"] = stats["sessions"]
        except Exception as e:
            health_status["database"] = f"error: {str(e)}"
            health_status["status"] = "degraded"
        
        return health_status
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Log configuration on startup
if __name__ == "__main__":
    logger.info(f"Starting RAG Assistant for organization: {config.organization_name}")
    logger.info(f"Configuration: {config.get_environment_info()}")
    
    if config.debug_mode:
        logger.info("Debug mode enabled")
    
    if not config.is_configured:
        logger.error("Critical configuration missing. Please check environment variables.")
        exit(1)
