import logging
import traceback
import log_config
from flask import Blueprint, jsonify, request
from extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from blueprints.leaning_routes import api_leaning_bp
from config import Config
from models import (Users, ContentViewingHistory, ContentPointRecord, ContentRelPages, LearningCompletionHistory
                    , ContentManager, ContentRelFolders, ContentRelChannels)
from sqlalchemy import text

@api_leaning_bp.route('/my_learning_rank', methods=['GET'])
@jwt_required(locations=['headers', 'cookies'])
def get_my_learning_rank():
    """
    사용자 학습 랭킹 조회
    Returns:
        JSON: 사용자 학습 랭킹
    """
    try:
        user_id = get_jwt_identity()
        
        min_seconds = Config.LEARNING_COMPLETED_MINUTES * 60  # Convert minutes to seconds
        
        query = text("""
                    WITH user_completed AS (
                        SELECT user_id, COUNT(*) AS completed_pages
                        FROM learning_completion_history
                        WHERE EXTRACT(EPOCH FROM total_duration) >= :min_seconds
                        GROUP BY user_id
                    )
                    SELECT COUNT(*) + 1 AS rank
                    FROM user_completed
                    WHERE completed_pages > (
                        SELECT COUNT(*)
                        FROM learning_completion_history
                        WHERE user_id = :user_id AND EXTRACT(EPOCH FROM total_duration) >= :min_seconds
                    )
                    """)
        
        result = db.session.execute(query, {'user_id': user_id, 'min_seconds': min_seconds})
        row = result.fetchone()
        logging.info(f"row: {row}")
        return jsonify({'rank': row['rank'] if row else 0}), 200
    except Exception as e:
        logging.error(f"Error in get_my_learning_rank: {str(e)}, {traceback.format_exc()}")
        return jsonify({"error": "Internal server error"}), 500

