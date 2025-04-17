from flask import Blueprint, jsonify, request
from extensions import db
from models import MemoReply, MemoData, Users
import logging
from datetime import datetime, timezone

api_memo_reply_bp = Blueprint('memo_reply', __name__)

@api_memo_reply_bp.route('/', methods=['POST'])
def create_memo_reply():
    try:
        data = request.json
        logging.info(f"Received POST request to /memo/reply with data: {data}")
        
        # Validate required fields
        if not all(key in data for key in ['memo_id', 'user_id', 'content']):
            return jsonify({"error": "Missing required fields"}), 400
            
        # Check if memo exists
        memo = MemoData.query.get(data['memo_id'])
        if not memo:
            return jsonify({"error": "Memo not found"}), 404
            
        # Create new reply
        reply = MemoReply(
            memo_id=data['memo_id'],
            user_id=data['user_id'],
            content=data['content']
        )
        
        db.session.add(reply)
        db.session.commit()
        
        logging.info(f"Successfully created memo reply with id: {reply.id}")
        return jsonify(reply.to_dict()), 201
    except Exception as e:
        logging.error(f"Error creating memo reply: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@api_memo_reply_bp.route('/memo/<memo_id>', methods=['GET'])
def get_replies_by_memo(memo_id):
    try:
        # Check if memo exists
        memo = MemoData.query.get_or_404(memo_id)
        
        # Get replies for this memo that are not deleted
        replies = MemoReply.query.filter_by(memo_id=memo_id, is_deleted=False).all()
        
        # Get user info for each reply
        result = []
        for reply in replies:
            reply_dict = reply.to_dict()
            user = Users.query.get(reply.user_id)
            if user:
                reply_dict['user'] = {
                    'id': user.id,
                    'name': user.name,
                    'position': user.position,
                    'department': user.department,
                    'company': user.company
                }
            result.append(reply_dict)
            
        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error retrieving memo replies: {str(e)}")
        return jsonify({"error": str(e)}), 500

@api_memo_reply_bp.route('/<id>', methods=['PUT'])
def update_reply(id):
    try:
        reply = MemoReply.query.get_or_404(id)
        data = request.json
        
        # Update content if provided
        if 'content' in data:
            reply.content = data['content']
            
        # Update timestamp
        reply.modified_at = datetime.now(timezone.utc)
        
        db.session.commit()
        logging.info(f"Successfully updated memo reply with id: {reply.id}")
        return jsonify(reply.to_dict()), 200
    except Exception as e:
        logging.error(f"Error updating memo reply: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@api_memo_reply_bp.route('/<id>', methods=['DELETE'])
def delete_reply(id):
    try:
        reply = MemoReply.query.get_or_404(id)
        
        # Soft delete by setting is_deleted flag
        reply.is_deleted = True
        db.session.commit()
        
        logging.info(f"Successfully deleted memo reply with id: {reply.id}")
        return '', 204
    except Exception as e:
        logging.error(f"Error deleting memo reply: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500 