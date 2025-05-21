import datetime
import logging
import log_config
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask import Blueprint, jsonify, request
from extensions import db, redis_client
from models import PushMessages
import json

api_push_bp = Blueprint('push', __name__)  # 블루프린트 생성

# 🔹 POST /leaning/push/send API 메시지 푸시
@api_push_bp.route('/send', methods=['POST'])
@jwt_required(locations=["headers","cookies"])
def send():
    data = request.get_json()
    user_ids = data.get('user_ids')
    title = data.get('title','')
    message = data.get('message')
    
    if not user_ids or not isinstance(user_ids, list):
        return jsonify({
            'status': 'error',
            'message': 'user_ids는 필수 항목이며 리스트여야 합니다.'
        }), 400
        
    if not message:
        return jsonify({
            'status': 'error',
            'message': 'message는 필수 항목입니다.'
        }), 400
        
    now = datetime.datetime.now(datetime.timezone.utc)
    messages = [
        PushMessages(user_id=uid, title=title, message=message, created_at=now)
        for uid in user_ids
    ]
    db.session.add_all(messages)
    db.session.commit()
    
    for msg in messages:
        if redis_client.exists(f"push_cache:{msg.user_id}"):           
            redis_client.rpush(f"push_cache:{msg.user_id}", json.dumps({
                'type':'push_message',
                'id': msg.id,
                'title': title,
                'message': message,     
                'created_at': msg.created_at.isoformat()  
            }))
            redis_client.ltrim(f"push_cache:{msg.user_id}", -20, -1)  # 최근 20개만 유지
            redis_client.expire(f"push_cache:{msg.user_id}", 600) # 10분 후 만료
        
    return jsonify({
        'status': 'success',
        'message': '푸시 알림이 성공적으로 전송되었습니다.'
    })
    
# 🔹 GET /leaning/push/check API 메시지 체크
@api_push_bp.route('/check', methods=['GET'])
@jwt_required(locations=["headers","cookies"])
def check():
    user_id = get_jwt_identity()
    redis_key = f"push_cache:{user_id}"
    
    
    if redis_client.exists(redis_key):
        redis_client.expire(redis_key, 600)  # Redis 키의 만료 시간을 10분으로 설정
        raw_messages = redis_client.lrange(redis_key, 0, -1)
        messages = [json.loads(msg) for msg in raw_messages]
        return jsonify({
            'status': 'success',
            'messages': messages
        })
        
    db_messages = PushMessages.query.filter_by(user_id=user_id).order_by(PushMessages.created_at.desc()).limit(20).all()
    messages = [msg.to_dict() for msg in db_messages]
    
    if messages:
        redis_client.set(redis_key, json.dumps(messages), ex=600)
        
    return jsonify({
        'status': 'success',
        'messages': messages
    })
        
    