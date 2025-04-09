from flask import Blueprint, jsonify, request
from extensions import db
from models import MemoData
import logging
from sqlalchemy import func
from datetime import datetime, timezone

api_memo_bp = Blueprint('memo', __name__)

@api_memo_bp.route('/', methods=['POST'])
def create_memo():
    try:
        data = request.json
        logging.info(f"Received POST request to /memo with data: {data}")
        
        # Get the maximum serial number and increment by 1
        max_serial = db.session.query(func.max(MemoData.serial_number)).scalar() or 0
        next_serial = max_serial + 1
        
        # Create memo with explicit values from request data
        memo = MemoData(
            id=str(data['id']),  # Ensure id is passed
            serial_number=next_serial,  # Set the next serial number
            modified_at=datetime.now(timezone.utc),  # Explicitly set modified_at to current time
            user_id=data.get('user_id'),
            content=data.get('content', ''),
            path=data.get('path'),
            rel_position_x=float(data['relPositionX']),  # Convert to float
            rel_position_y=float(data['relPositionY']),
            world_position_x=float(data['worldPositionX']),
            world_position_y=float(data['worldPositionY']),
            world_position_z=float(data['worldPositionZ']),
            status=int(data['status'])  # Convert to int
        )
        
        db.session.add(memo)
        db.session.commit()
        logging.info(f"Successfully created memo with id: {memo.id}")
        return jsonify({
            "success": True,
            "message": "Memo created successfully",
            "serial_number": memo.serial_number
        }), 201
    except Exception as e:
        logging.error(f"Error creating memo: {str(e)}")
        db.session.rollback()  # Rollback on error
        return jsonify({"error": str(e)}), 500

@api_memo_bp.route('/', methods=['GET'])
def get_all_memos():
    try:
        logging.info("Received GET request to /memo")
        user_id = request.args.get('user_id')
        path = request.args.get('path')

        query = MemoData.query
        if user_id:
            query = query.filter(MemoData.user_id == user_id)
        if path:
            query = query.filter(MemoData.path == path)

        memos = query.all()
        memos_list = [memo.to_dict() for memo in memos]
        return jsonify(memos_list), 200
    except Exception as e:
        logging.error(f"Error retrieving memos: {str(e)}")
        return jsonify({"error": str(e)}), 500

@api_memo_bp.route('/<id>', methods=['GET'])
def get_memo(id):
    memo = MemoData.query.get_or_404(id)
    return jsonify(memo.to_dict())

@api_memo_bp.route('/<id>', methods=['PUT'])
def update_memo(id):
    try:
        memo = MemoData.query.get_or_404(id)
        data = request.json
        logging.info(f"Received PUT request to /memo/{id} with data: {data}")
        
        # Update fields matching the JSON case
        memo.content = data.get('content', memo.content)
        memo.user_id = data.get('user_id', memo.user_id)
        memo.path = data.get('path', memo.path)
        memo.rel_position_x = data.get('relPositionX', memo.rel_position_x)
        memo.rel_position_y = data.get('relPositionY', memo.rel_position_y)
        memo.world_position_x = data.get('worldPositionX', memo.world_position_x)
        memo.world_position_y = data.get('worldPositionY', memo.world_position_y)
        memo.world_position_z = data.get('worldPositionZ', memo.world_position_z)
        memo.status = data.get('status', memo.status)
        
        db.session.commit()
        logging.info(f"Successfully updated memo with id: {memo.id}")
        return jsonify(memo.to_dict()), 200
    except Exception as e:
        logging.error(f"Error updating memo: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@api_memo_bp.route('/<id>', methods=['DELETE'])
def delete_memo(id):
    memo = MemoData.query.get_or_404(id)
    db.session.delete(memo)
    db.session.commit()
    return '', 204 