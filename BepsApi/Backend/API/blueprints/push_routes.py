import datetime
import logging
import log_config
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask import Blueprint, jsonify, request
from extensions import db, redis_client
from models import PushMessages, Users
import json
from config import Config

api_push_bp = Blueprint('push', __name__)  # 블루프린트 생성

# 🔹 POST /leaning/push/send API 메시지 푸시
@api_push_bp.route('/send', methods=['POST'])
@jwt_required(locations=["headers","cookies"])
def send():
    data = request.get_json()
    filter_type = data.get('filter_type')
    filter_value = data.get('filter_value')
    title = data.get('title','')
    message = data.get('message')
    
    if not filter_type:
        return jsonify({
            'status': 'error',
            'message': 'filter_type은 필수 항목입니다.'
        }), 400
    
    if filter_type != 'all' and not filter_value:
        return jsonify({
            'status': 'error',
            'message': 'filter_value는 필수 항목입니다.'
        }), 400
        
    if not message:
        return jsonify({
            'status': 'error',
            'message': 'message는 필수 항목입니다.'
        }), 400
    
    query = db.session.query(Users.id)
    
    if filter_type == 'company':
        query = query.filter(Users.company == filter_value)
    elif filter_type == 'department':
        query = query.filter(Users.department == filter_value)
    elif filter_type == 'user':
        query = query.filter(Users.id == filter_value)
    
    user_ids = [user.id for user in query.all()]
    if not user_ids:
        return jsonify({
            'status': 'error',
            'message': '해당 조건에 맞는 사용자가 없습니다.'
        }), 404
    
    now = datetime.datetime.now(datetime.timezone.utc)
    messages = [
        PushMessages(user_id=uid, title=title, message=message, created_at=now)
        for uid in user_ids
    ]
    db.session.add_all(messages)
    db.session.commit()
    
    for msg in messages:
        if redis_client.exists(f"push_cache:{msg.user_id}"):        
            length = redis_client.llen(f"push_cache:{msg.user_id}") # 현재 푸시 메시지 개수 확인
            # 푸시 메시지 개수가 제한을 초과하면 가장 오래된 메시지를 삭제
            if length >= Config.PUSH_MESSAGE_LIMIT: 
                redis_client.lpop(f"push_cache:{msg.user_id}")
                   
            redis_client.rpush(f"push_cache:{msg.user_id}", json.dumps({
                'id': msg.id,
                'title': title,
                'message': message,     
                'created_at': msg.created_at.isoformat(),
                'user_id': msg.user_id,
                'is_read': msg.is_read
            }))
            redis_client.expire(f"push_cache:{msg.user_id}", 600) # 10분 후 만료
    
    for uid in user_ids:
        trim_old_push_messages(uid, Config.PUSH_MESSAGE_LIMIT)
        
    return jsonify({
        'status': 'success',
        'message': '푸시 알림이 성공적으로 전송되었습니다.'
    })

def trim_old_push_messages(user_id, limit):
    """오래된 푸시 메시지를 삭제하는 함수"""
    old_messages = db.session.query(PushMessages).filter(
        PushMessages.user_id == user_id
        ).order_by(PushMessages.created_at.desc()).offset(limit).all()
    for msg in old_messages:
        db.session.delete(msg)
    db.session.commit()
    
    
# 🔹 GET /leaning/push/load API 메시지 로드
@api_push_bp.route('/load', methods=['GET'])
@jwt_required(locations=["headers","cookies"])
def load():
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
        
    db_messages = PushMessages.query.filter_by(user_id=user_id).order_by(PushMessages.created_at.desc()).limit(Config.PUSH_MESSAGE_LIMIT).all()
    messages = [msg.to_dict() for msg in db_messages]
    
    if messages:
       for msg in reversed(messages):   # 메시지를 오래된 순으로 redis에 저장(lpop은 가장 오래된 메시지를 삭제)
           redis_client.rpush(redis_key, json.dumps(msg))
       redis_client.expire(redis_key, 600)  # Redis 키의 만료 시간을 10분으로 설정
       redis_client.ltrim(redis_key, -5, -1)  # 최근 5개만 유지
        
    return jsonify({
        'status': 'success',
        'messages': messages
    })

# 🔹 GET /leaning/push/read API 읽은 푸시 메시지 처리    
@api_push_bp.route('/read', methods=['GET'])
@jwt_required(locations=["headers","cookies"])
def read():
    user_id = get_jwt_identity()
    redis_key = f"push_cache:{user_id}"
    
    if not redis_client.exists(redis_key):
        return jsonify({
            'status': 'error',
            'message': '읽을 푸시 메시지가 없습니다. /leaning/push/check API를 먼저 호출해주세요.'
        }), 404
    
    raw_messages = redis_client.lrange(redis_key, 0, -1)
    messages = [json.loads(msg) for msg in raw_messages]
    
    unread_ids = [msg['id'] for msg in messages if not msg.get('is_read')]
    now = datetime.datetime.now(datetime.timezone.utc)
    
    if unread_ids:
        PushMessages.query.filter(
            PushMessages.id.in_(unread_ids),
            PushMessages.user_id == user_id,
            PushMessages.is_read == False
        ).update({
            'is_read': True
        }, synchronize_session=False)
        db.session.commit()
        
    for m in messages:
        if m['id'] in unread_ids:
            m['is_read'] = True
    
    redis_client.delete(redis_key)
    for m in messages:
        redis_client.rpush(redis_key, json.dumps(m))
    redis_client.ltrim(redis_key, -Config.PUSH_MESSAGE_LIMIT, -1)
    redis_client.expire(redis_key, 600)

# 🔹 GET /leaning/push/count API 푸시 메시지 개수 확인   
@api_push_bp.route('/count', methods=['GET'])
@jwt_required(locations=["headers","cookies"])
def count():
    user_id = get_jwt_identity()
    redis_key = f"push_cache:{user_id}"
    
    if redis_client.exists(redis_key):
        count = redis_client.llen(redis_key)
        return jsonify({
            'status': 'success',
            'count': count
        })
    else:
        return jsonify({
            'status': 'not_loaded',
            'message': '/leaning/push/load API를 먼저 호출해주세요.',
            'count': 0
        }), 404