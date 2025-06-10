from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import MemoData, Users
import logging
from sqlalchemy import func, text
import traceback
from datetime import datetime, timezone, time

api_memo_bp = Blueprint('memo', __name__)

@api_memo_bp.route('/', methods=['POST'])
def create_memo():
    try:
        data = request.json
        logging.info(f"Received POST request to /memo with data: {data}")
        
        modified_at = datetime.now(timezone.utc)
        # Create memo with explicit values from request data
        memo = MemoData(
            modified_at=modified_at,  # Explicitly set modified_at to current time
            user_id=data.get('user_id'),
            title=data.get('title'),
            content=data.get('content', ''),
            path=data.get('path'),
            file_id=data.get('file_id'),
            folder_id=data.get('folder_id'),
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
            "modified_at": modified_at,
            "id": memo.id
        }), 201
    except Exception as e:
        logging.error(f"Error creating memo: {str(e)}")
        db.session.rollback()  # Rollback on error
        return jsonify({"error": str(e)}), 500

@api_memo_bp.route('/', methods=['GET'])
@jwt_required(locations=['headers','cookies'])
def get_all_memos():
    try:
        logging.info("Received GET request to /memo")
        user_id = request.args.get('user_id')
        path = request.args.get('path')
        file_id = request.args.get('file_id')
        folder_id = request.args.get('folder_id')
        
        logging.info(f"Request parameters: user_id={user_id}, path={path}, file_id={file_id}, folder_id={folder_id}")
        
        # Get JWT identity (user_id from token)
        jwt_user_id = get_jwt_identity()
        logging.info(f"Authenticated user_id: {jwt_user_id}")
        
        # Fetch user information to check role
        user = Users.query.filter_by(id=jwt_user_id).first()
        
        if not user:
            logging.error(f"User not found for ID: {jwt_user_id}")
            return jsonify({"error": "User not found"}), 404
        
        logging.info(f"User role_id: {user.role_id}")
        
        # Base query
        query = MemoData.query
        
        # Apply filters based on parameters
        if path:
            query = query.filter(MemoData.path == path)
        if file_id:
            query = query.filter(MemoData.file_id == file_id)
        if folder_id:
            query = query.filter(MemoData.folder_id == folder_id)
            
        # If role_id is null, user can see only their own memos
        if user.role_id is None:
            query = query.filter(MemoData.user_id == jwt_user_id)
        else:
            # If role_id is not null (user is a manager)
            try:
                managed_memos_query = """
                    SELECT m.id
                    FROM memos m
                    JOIN content_manager cm ON 
                        (cm.type = 'file' AND cm.file_id = m.file_id AND m.file_id IS NOT NULL) OR 
                        (cm.type = 'folder' AND cm.folder_id = m.folder_id AND m.folder_id IS NOT NULL)
                    WHERE cm.user_id = :user_id
                """
                
                logging.info(f"Executing content_manager query for user_id: {jwt_user_id}")
                managed_memos = db.session.execute(text(managed_memos_query), {"user_id": jwt_user_id}).all()
                managed_memo_ids = [memo[0] for memo in managed_memos]
                logging.info(f"Found {len(managed_memo_ids)} managed memos for user_id: {jwt_user_id}")
                
                # Combine user's own memos and managed memos
                if managed_memo_ids:
                    query = query.filter(
                        (MemoData.user_id == jwt_user_id) | 
                        (MemoData.id.in_(managed_memo_ids))
                    )
                else:
                    # If no managed memos, just show user's own memos
                    query = query.filter(MemoData.user_id == jwt_user_id)
            except Exception as e:
                logging.error(f"Error querying content_manager: {str(e)}")
                # If the query fails, fall back to showing only the user's own memos
                query = query.filter(MemoData.user_id == jwt_user_id)
        
        # Initialize memos as empty list
        memos = []
        
        # Handle user_id case-insensitive search
        if user_id:
            # First try with the exact user_id
            first_query = query.filter(MemoData.user_id == user_id)
            memos = first_query.all()
            
            # If no results and user_id contains letters, try alternative case
            if not memos and any(c.isalpha() for c in user_id):
                import re
                # Extract letters and numbers
                match = re.match(r'([a-zA-Z]+)(\d+)', user_id)
                if match:
                    letters, numbers = match.groups()
                    # Try opposite case (upper if lower, lower if upper)
                    if letters.islower():
                        alt_user_id = letters.upper() + numbers
                    else:
                        alt_user_id = letters.lower() + numbers
                    
                    logging.info(f"No results for user_id: {user_id}, trying alternative: {alt_user_id}")
                    memos = query.filter(MemoData.user_id == alt_user_id).all()
        else:
            # If no user_id provided, use the query we've built
            memos = query.all()
            
        memos_list = [memo.to_dict() for memo in memos]
        logging.info(f"Returning {len(memos_list)} memos")
        return jsonify(memos_list), 200
    except Exception as e:
        logging.error(f"Error retrieving memos: {str(e)}")
        return jsonify({"error": str(e)}), 500

@api_memo_bp.route('/<int:id>', methods=['GET'])
def get_memo(id):
    memo = MemoData.query.get_or_404(id)
    return jsonify(memo.to_dict())

@api_memo_bp.route('/<int:id>', methods=['PUT'])
def update_memo(id):
    try:
        memo = MemoData.query.get_or_404(id)
        data = request.json
        logging.info(f"Received PUT request to /memo/{id} with data: {data}")
        
        # Update fields matching the JSON case
        memo.content = data.get('content', memo.content)
        memo.title = data.get('title', memo.title)
        memo.user_id = data.get('user_id', memo.user_id)
        memo.path = data.get('path', memo.path)
        memo.file_id = data.get('file_id', memo.file_id)
        memo.folder_id = data.get('folder_id', memo.folder_id)
        memo.rel_position_x = data.get('relPositionX', memo.rel_position_x)
        memo.rel_position_y = data.get('relPositionY', memo.rel_position_y)
        memo.world_position_x = data.get('worldPositionX', memo.world_position_x)
        memo.world_position_y = data.get('worldPositionY', memo.world_position_y)
        memo.world_position_z = data.get('worldPositionZ', memo.world_position_z)
        memo.status = data.get('status', memo.status)
        
        # Update modified_at timestamp
        memo.modified_at = datetime.now(timezone.utc)
        
        db.session.commit()
        logging.info(f"Successfully updated memo with id: {memo.id}")
        return jsonify(memo.to_dict()), 200
    except Exception as e:
        logging.error(f"Error updating memo: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@api_memo_bp.route('/<int:id>', methods=['DELETE'])
def delete_memo(id):
    memo = MemoData.query.get_or_404(id)
    db.session.delete(memo)
    db.session.commit()
    return '', 204 


# 🔹 GET /leaning/memo_rank API 메모 랭킹 조회    
@api_memo_bp.route('/memo_rank', methods=['GET'])
@jwt_required(locations=['headers','cookies'])  # 🔹 JWT 검증을 먼저 수행
def memo_rank():
    from services.user_summary_service import get_period_value
    try:
        filter_type = request.args.get('filter_type', 'all')
        filter_value = request.args.get('filter_value')
        period_type = request.args.get('period_type', 'year')
        period_value = request.args.get('period_value')
        
        if not period_type or not period_value:
            return jsonify({'error': 'Please provide scope, period_type, and period_value'}), 400
        
        start_dt, end_dt = get_period_value(period_type, period_value)
        local_tz = datetime.now().astimezone().tzinfo
        utc_start_dt = datetime.combine(start_dt, time.min, tzinfo=local_tz).astimezone(timezone.utc)
        utc_end_dt = datetime.combine(end_dt, time.max, tzinfo=local_tz).astimezone(timezone.utc)                  
        
        base_query = """
            SELECT m.file_id AS item, COUNT(*) AS cnt, f.name AS name, d.name AS folder_name, ch.name AS channel_name, MAX(m.modified_at) AS modified_at
            FROM memos m
            JOIN users u ON m.user_id = u.id
            JOIN content_rel_pages f ON m.file_id = f.id
            JOIN content_rel_folders d ON f.folder_id = d.id
            JOIN content_rel_channels ch ON d.channel_id = ch.id
            WHERE m.modified_at BETWEEN :start_date AND :end_date AND m.file_id IS NOT NULL AND {filter_clause}
            GROUP BY m.file_id, f.name, d.name, ch.name
            ORDER BY cnt DESC, file_id ASC
            LIMIT 5
            """
        
        params = {
            'start_date': utc_start_dt,
            'end_date': utc_end_dt
        }
        
        if filter_type == 'company':
            filter_clause = "u.company = :filter_value"
            params['filter_value'] = filter_value
        elif filter_type == 'department':
            filter_clause = "u.company = :company AND u.department = :department"
            company, department = filter_value.split('||')
            params['company'] = company
            params['department'] = department
        elif filter_type == 'user':
            filter_clause = "u.id = :filter_value"
            params['filter_value'] = filter_value
        else:
            filter_clause = "1=1"
        
        query = text(base_query.format(filter_clause=filter_clause))
                 
        result = db.session.execute(query, params).mappings().all()
        if not result:
            return jsonify({'error': 'No data found'}), 404
        
        return jsonify({'data': [dict(row) for row in result]}), 200  # 200: OK
    
    except Exception as e:
        logging.error(f"[memo_rank] error: {str(e)}, {traceback.format_exc()}")
        return jsonify({'[memo_rank] error': str(e)}), 500
