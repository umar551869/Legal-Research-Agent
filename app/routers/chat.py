import asyncio
import json
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from app.models import ChatRequest, ConversationBase, ConversationDetail, MessageBase
from app.dependencies import get_current_user, UserProfile
from app.services.research import research_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("/query")
async def chat_query(
    payload: ChatRequest, 
    http_request: Request,
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Streaming research query endpoint with conversation memory.
    
    SSE protocol:
      - First event: JSON with {sources, conversation_id, intent}
      - Subsequent events: JSON with {token: "..."} for each text chunk
      - Error event: JSON with {error: "..."}
      - Final event: data: [DONE]
    """
    limiter = http_request.app.state.limiter
    
    @limiter.limit("10/minute")
    async def run_streaming_logic(request: Request):
        async def event_generator():
            try:
                async for chunk in research_service.run_research_stream(
                    payload.query, 
                    user_id=current_user.id,
                    scope=payload.scope,
                    conversation_id=payload.conversation_id,
                    token=current_user.token
                ):
                    chunk_str = chunk.strip()
                    if chunk_str.startswith("{") and chunk_str.endswith("}"):
                        # Chunk is JSON metadata - forward directly
                        yield f"data: {chunk_str}\n\n"
                    else:
                        # Chunk is raw text token - wrap in JSON
                        yield f"data: {json.dumps({'token': chunk})}\n\n"
            except Exception as e:
                logger.error(f"Chat Query Stream Error: {e}", exc_info=True)
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
            finally:
                yield "data: [DONE]\n\n"
        
        return StreamingResponse(event_generator(), media_type="text/event-stream")

    return await run_streaming_logic(request=http_request)

@router.get("/conversations", response_model=List[ConversationBase])
async def list_conversations(current_user: UserProfile = Depends(get_current_user)):
    """List all research conversations for the user (Database + Stateless Fallback)."""
    conversations = await research_service.list_stateless_conversations(current_user.id)
    
    try:
        client = research_service._get_db_client(current_user.token)
        res = await asyncio.to_thread(
            lambda: client.table("conversations")
                .select("*")
                .eq("user_id", current_user.id)
                .order("updated_at", desc=True)
                .execute()
        )
        if res.data:
            # Only add DB conversations not already in stateless set
            stateless_ids = {c["id"] for c in conversations}
            for c in res.data:
                if c["id"] not in stateless_ids:
                    conversations.append(c)
    except Exception as e:
        logger.warning(f"Supabase unavailable for list_conversations: {e}")
    
    conversations.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return conversations

@router.get("/conversation/{conv_id}", response_model=ConversationDetail)
async def get_conversation_detail(
    conv_id: str,
    current_user: UserProfile = Depends(get_current_user)
):
    """Retrieve full conversation detail (Database or Stateless Fallback)."""
    messages: List[MessageBase] = []
    title = "Untitled Research"
    created_at = None
    updated_at = None

    if conv_id in research_service.stateless_conversations:
        conv_data = research_service.stateless_conversations[conv_id]
        if conv_data.get("user_id") != current_user.id:
            raise HTTPException(status_code=404, detail="Conversation not found")

        messages = [
            MessageBase(
                id=f"msg-{i}", 
                role=m["role"], 
                content=m["content"],
                sources=m.get("sources"),
                created_at=m.get("created_at"),
            ) for i, m in enumerate(conv_data["messages"])
        ]
        title = conv_data.get("title", title)
        created_at = conv_data.get("created_at", conv_data.get("updated_at"))
        updated_at = conv_data.get("updated_at")
    else:
        try:
            client = research_service._get_db_client(current_user.token)
            # Fetch conversation metadata
            conv_res = await asyncio.to_thread(
                lambda: client.table("conversations")
                    .select("*")
                    .eq("id", conv_id)
                    .single()
                    .execute()
            )
            
            if conv_res.data and conv_res.data["user_id"] == current_user.id:
                title = conv_res.data.get("title", title)
                created_at = conv_res.data.get("created_at")
                updated_at = conv_res.data.get("updated_at")
                
                # Fetch messages
                msg_res = await asyncio.to_thread(
                    lambda: client.table("messages")
                        .select("*")
                        .eq("conversation_id", conv_id)
                        .order("created_at", desc=False)
                        .execute()
                )
                messages = [
                    MessageBase(
                        id=m["id"],
                        role=m["role"],
                        content=m["content"],
                        sources=m.get("sources"),
                        created_at=m["created_at"]
                    ) for m in msg_res.data
                ]
            else:
                raise HTTPException(status_code=404, detail="Conversation not found")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching DB history: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch history")
    
    return ConversationDetail(
        id=conv_id,
        title=title,
        created_at=created_at,
        updated_at=updated_at,
        message_count=len(messages),
        messages=messages
    )

@router.delete("/conversation/{conv_id}")
async def delete_conversation(
    conv_id: str,
    current_user: UserProfile = Depends(get_current_user)
):
    """Delete a conversation."""
    if conv_id in research_service.stateless_conversations:
        if research_service.stateless_conversations[conv_id].get("user_id") != current_user.id:
            raise HTTPException(status_code=404, detail="Conversation not found")
        del research_service.stateless_conversations[conv_id]
        
    try:
        client = research_service._get_db_client(current_user.token)
        await asyncio.to_thread(
            lambda: client.table("conversations")
                .delete()
                .eq("id", conv_id)
                .eq("user_id", current_user.id)
                .execute()
        )
    except Exception:
        pass
    
    return {"status": "success"}
