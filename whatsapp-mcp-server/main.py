import sqlite3
from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP
import requests
from whatsapp import MESSAGES_DB_PATH, WHATSAPP_API_BASE_URL
from whatsapp import (
    search_contacts as whatsapp_search_contacts,
    list_messages as whatsapp_list_messages,
    list_chats as whatsapp_list_chats,
    get_chat as whatsapp_get_chat,
    get_direct_chat_by_contact as whatsapp_get_direct_chat_by_contact,
    get_contact_chats as whatsapp_get_contact_chats,
    get_last_interaction as whatsapp_get_last_interaction,
    get_message_context as whatsapp_get_message_context,
    send_message as whatsapp_send_message,
    send_file as whatsapp_send_file,
    send_audio_message as whatsapp_audio_voice_message,
    download_media as whatsapp_download_media
)

# Initialize FastMCP server
mcp = FastMCP("whatsapp")

@mcp.tool()
def search_contacts(query: str) -> List[Dict[str, Any]]:
    """Search WhatsApp contacts by name or phone number.
    
    Args:
        query: Search term to match against contact names or phone numbers
    """
    contacts = whatsapp_search_contacts(query)
    return contacts

@mcp.tool()
def list_messages(
    after: Optional[str] = None,
    before: Optional[str] = None,
    sender_phone_number: Optional[str] = None,
    chat_jid: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_context: bool = True,
    context_before: int = 1,
    context_after: int = 1
) -> List[Dict[str, Any]]:
    """Get WhatsApp messages matching specified criteria with optional context.
    
    Args:
        after: Optional ISO-8601 formatted string to only return messages after this date
        before: Optional ISO-8601 formatted string to only return messages before this date
        sender_phone_number: Optional phone number to filter messages by sender
        chat_jid: Optional chat JID to filter messages by chat
        query: Optional search term to filter messages by content
        limit: Maximum number of messages to return (default 20)
        page: Page number for pagination (default 0)
        include_context: Whether to include messages before and after matches (default True)
        context_before: Number of messages to include before each match (default 1)
        context_after: Number of messages to include after each match (default 1)
    """
    messages = whatsapp_list_messages(
        after=after,
        before=before,
        sender_phone_number=sender_phone_number,
        chat_jid=chat_jid,
        query=query,
        limit=limit,
        page=page,
        include_context=include_context,
        context_before=context_before,
        context_after=context_after
    )
    return messages

@mcp.tool()
def list_chats(
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_last_message: bool = True,
    sort_by: str = "last_active"
) -> List[Dict[str, Any]]:
    """Get WhatsApp chats matching specified criteria.
    
    Args:
        query: Optional search term to filter chats by name or JID
        limit: Maximum number of chats to return (default 20)
        page: Page number for pagination (default 0)
        include_last_message: Whether to include the last message in each chat (default True)
        sort_by: Field to sort results by, either "last_active" or "name" (default "last_active")
    """
    chats = whatsapp_list_chats(
        query=query,
        limit=limit,
        page=page,
        include_last_message=include_last_message,
        sort_by=sort_by
    )
    return chats

@mcp.tool()
def get_chat(chat_jid: str, include_last_message: bool = True) -> Dict[str, Any]:
    """Get WhatsApp chat metadata by JID.
    
    Args:
        chat_jid: The JID of the chat to retrieve
        include_last_message: Whether to include the last message (default True)
    """
    chat = whatsapp_get_chat(chat_jid, include_last_message)
    return chat

@mcp.tool()
def get_direct_chat_by_contact(sender_phone_number: str) -> Dict[str, Any]:
    """Get WhatsApp chat metadata by sender phone number.
    
    Args:
        sender_phone_number: The phone number to search for
    """
    chat = whatsapp_get_direct_chat_by_contact(sender_phone_number)
    return chat

@mcp.tool()
def get_contact_chats(jid: str, limit: int = 20, page: int = 0) -> List[Dict[str, Any]]:
    """Get all WhatsApp chats involving the contact.
    
    Args:
        jid: The contact's JID to search for
        limit: Maximum number of chats to return (default 20)
        page: Page number for pagination (default 0)
    """
    chats = whatsapp_get_contact_chats(jid, limit, page)
    return chats

@mcp.tool()
def get_last_interaction(jid: str) -> str:
    """Get most recent WhatsApp message involving the contact.
    
    Args:
        jid: The JID of the contact to search for
    """
    message = whatsapp_get_last_interaction(jid)
    return message

@mcp.tool()
def get_message_context(
    message_id: str,
    before: int = 5,
    after: int = 5
) -> Dict[str, Any]:
    """Get context around a specific WhatsApp message.
    
    Args:
        message_id: The ID of the message to get context for
        before: Number of messages to include before the target message (default 5)
        after: Number of messages to include after the target message (default 5)
    """
    context = whatsapp_get_message_context(message_id, before, after)
    return context

def _resolve_mentions(mentions: list[str] = None) -> tuple[list[str] | None, str | None]:
    """Resolve phone numbers in mentions to LID JIDs. Returns (resolved_jids, error)."""
    if not mentions:
        return None, None

    resolved = []
    for m in mentions:
        if "@" in m:
            # Already a JID, use as-is
            resolved.append(m)
        else:
            # Phone number - look up LID
            try:
                db = sqlite3.connect(MESSAGES_DB_PATH)
                cursor = db.cursor()
                cursor.execute("""
                    SELECT DISTINCT m2.sender FROM messages m1
                    JOIN messages m2 ON m1.chat_jid = m2.chat_jid
                    WHERE m1.sender = ? AND m2.sender LIKE '%@lid'
                    AND m2.sender != m1.sender
                    ORDER BY MAX(m2.timestamp) DESC
                    LIMIT 1
                """, (m,))
                row = cursor.fetchone()
                db.close()

                if row:
                    resolved.append(row[0] if "@" in row[0] else f"{row[0]}@lid")
                else:
                    # Try finding in direct chat
                    db = sqlite3.connect(MESSAGES_DB_PATH)
                    cursor = db.cursor()
                    cursor.execute("""
                        SELECT DISTINCT sender FROM messages
                        WHERE sender LIKE '%@lid'
                        AND chat_jid = ?
                        ORDER BY timestamp DESC LIMIT 1
                    """, (f"{m}@s.whatsapp.net",))
                    row = cursor.fetchone()
                    db.close()

                    if row:
                        resolved.append(row[0] if "@" in row[0] else f"{row[0]}@lid")
                    else:
                        return None, f"LID bulunamadı: {m}. Bu kişi ortak bir grupta mesaj atmamış olabilir."
            except Exception as e:
                return None, f"LID arama hatası: {str(e)}"

    return resolved, None


@mcp.tool()
def send_message(
    recipient: str,
    message: str,
    quoted_message_id: str = None,
    quoted_chat_jid: str = None,
    mentions: list[str] = None
) -> Dict[str, Any]:
    """Send a WhatsApp message to a person or group. For group chats use the JID.

    Args:
        recipient: The recipient - either a phone number with country code but no + or other symbols,
                 or a JID (e.g., "123456789@s.whatsapp.net" or a group JID like "123456789@g.us")
        message: The message text to send
        quoted_message_id: Optional message ID to reply to (quote reply)
        quoted_chat_jid: Optional chat JID where the quoted message is from
        mentions: Optional list of phone numbers to mention (e.g., ["905551234567"]). Automatically resolved to LID JIDs.

    Returns:
        A dictionary containing success status and a status message
    """
    if not recipient:
        return {
            "success": False,
            "message": "Recipient must be provided"
        }

    # Resolve phone numbers to LID JIDs
    resolved_mentions, error = _resolve_mentions(mentions)
    if error:
        return {"success": False, "message": error}

    success, status_message = whatsapp_send_message(recipient, message, quoted_message_id, quoted_chat_jid, resolved_mentions)
    return {
        "success": success,
        "message": status_message
    }

@mcp.tool()
def send_file(
    recipient: str,
    media_path: str,
    message: str = "",
    quoted_message_id: str = None,
    quoted_chat_jid: str = None,
    mentions: list[str] = None
) -> Dict[str, Any]:
    """Send a file such as a picture, raw audio, video or document via WhatsApp to the specified recipient. For group messages use the JID.

    Args:
        recipient: The recipient - either a phone number with country code but no + or other symbols,
                 or a JID (e.g., "123456789@s.whatsapp.net" or a group JID like "123456789@g.us")
        media_path: The absolute path to the media file to send (image, video, document)
        message: Optional caption text for the media
        quoted_message_id: Optional message ID to reply to (quote reply)
        quoted_chat_jid: Optional chat JID where the quoted message is from
        mentions: Optional list of phone numbers to mention (e.g., ["905551234567"])

    Returns:
        A dictionary containing success status and a status message
    """
    resolved_mentions, error = _resolve_mentions(mentions)
    if error:
        return {"success": False, "message": error}

    success, status_message = whatsapp_send_file(recipient, media_path, message, quoted_message_id, quoted_chat_jid)
    return {
        "success": success,
        "message": status_message
    }

@mcp.tool()
def send_audio_message(recipient: str, media_path: str) -> Dict[str, Any]:
    """Send any audio file as a WhatsApp audio message to the specified recipient. For group messages use the JID. If it errors due to ffmpeg not being installed, use send_file instead.
    
    Args:
        recipient: The recipient - either a phone number with country code but no + or other symbols,
                 or a JID (e.g., "123456789@s.whatsapp.net" or a group JID like "123456789@g.us")
        media_path: The absolute path to the audio file to send (will be converted to Opus .ogg if it's not a .ogg file)
    
    Returns:
        A dictionary containing success status and a status message
    """
    success, status_message = whatsapp_audio_voice_message(recipient, media_path)
    return {
        "success": success,
        "message": status_message
    }

@mcp.tool()
def get_contact_lid(phone_number: str) -> Dict[str, Any]:
    """Find a contact's LID (Linked ID) JID from message history. LID JIDs are needed for mentions in group chats.

    Args:
        phone_number: Phone number to search for (with country code, no + symbol)

    Returns:
        A dictionary containing the LID JID if found
    """
    try:
        db = sqlite3.connect(MESSAGES_DB_PATH)
        cursor = db.cursor()
        # Search for LID sender in messages where phone number appears in the chat or as sender
        cursor.execute("""
            SELECT DISTINCT sender FROM messages
            WHERE sender LIKE '%@lid'
            AND chat_jid IN (
                SELECT DISTINCT chat_jid FROM messages WHERE sender = ? OR chat_jid LIKE ?
            )
            ORDER BY timestamp DESC
        """, (phone_number, f"%{phone_number}%"))
        lids = [row[0] for row in cursor.fetchall()]
        db.close()

        if lids:
            return {
                "success": True,
                "phone_number": phone_number,
                "lid_jids": [f"{lid}@lid" if "@" not in lid else lid for lid in lids],
                "message": f"Found {len(lids)} LID(s) for {phone_number}"
            }
        else:
            # Try direct search by phone in sender field
            db = sqlite3.connect(MESSAGES_DB_PATH)
            cursor = db.cursor()
            cursor.execute("""
                SELECT DISTINCT m2.sender FROM messages m1
                JOIN messages m2 ON m1.chat_jid = m2.chat_jid
                WHERE m1.sender = ? AND m2.sender LIKE '%@lid'
                GROUP BY m2.sender
                ORDER BY MAX(m2.timestamp) DESC
            """, (phone_number,))
            lids = [row[0] for row in cursor.fetchall()]
            db.close()

            if lids:
                return {
                    "success": True,
                    "phone_number": phone_number,
                    "lid_jids": [f"{lid}" if "@" in lid else f"{lid}@lid" for lid in lids],
                    "message": f"Found {len(lids)} LID(s) in shared groups"
                }

            return {
                "success": False,
                "message": f"No LID found for {phone_number}. The contact may not have sent messages in any shared groups yet."
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

@mcp.tool()
def download_media(message_id: str, chat_jid: str) -> Dict[str, Any]:
    """Download media from a WhatsApp message and get the local file path.
    
    Args:
        message_id: The ID of the message containing the media
        chat_jid: The JID of the chat containing the message
    
    Returns:
        A dictionary containing success status, a status message, and the file path if successful
    """
    file_path = whatsapp_download_media(message_id, chat_jid)
    
    if file_path:
        return {
            "success": True,
            "message": "Media downloaded successfully",
            "file_path": file_path
        }
    else:
        return {
            "success": False,
            "message": "Failed to download media"
        }

@mcp.tool()
def refresh_chats() -> Dict[str, Any]:
    """Refresh all chat names and group info from WhatsApp. Updates chat list with latest group names and contact info."""
    try:
        url = f"{WHATSAPP_API_BASE_URL}/refresh-chats"
        response = requests.post(url)
        if response.status_code == 200:
            return response.json()
        return {"success": False, "message": f"Error: HTTP {response.status_code}"}
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool()
def reset_messages() -> Dict[str, Any]:
    """Clear all stored messages from the database. Chat history will rebuild as new messages arrive. Use this to fix stale/corrupted message data."""
    try:
        url = f"{WHATSAPP_API_BASE_URL}/reset-messages"
        response = requests.post(url)
        if response.status_code == 200:
            return response.json()
        return {"success": False, "message": f"Error: HTTP {response.status_code}"}
    except Exception as e:
        return {"success": False, "message": str(e)}

@mcp.tool()
def get_chat_info(chat_jid: str) -> Dict[str, Any]:
    """Get detailed info about a chat or group including participants, topic, and admin status.

    Args:
        chat_jid: The JID of the chat (e.g., "120363xxx@g.us" for groups)

    Returns:
        Chat/group details including name, participants, and metadata
    """
    try:
        url = f"{WHATSAPP_API_BASE_URL}/chat-info"
        response = requests.post(url, json={"chat_jid": chat_jid})
        if response.status_code == 200:
            return response.json()
        return {"success": False, "message": f"Error: HTTP {response.status_code}"}
    except Exception as e:
        return {"success": False, "message": str(e)}

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')