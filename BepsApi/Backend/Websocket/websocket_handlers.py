import asyncio
import websockets
import json
import time
import logging
import log_config
import requests

all_clients = set()     # 모든 클라이언트 (로그인 여부와 관계없이)
active_users = {}       # 로그인한 클라이언트 {sid: {"user_id": ID, "ip": IP, "last_active": timestamp}}
TIMEOUT = 40           # 클라이언트 타임아웃 시간 (초)
PING_INTERVAL = 10       # 클라이언트에게 PING 메시지를 보내는 간격 (초)
CHECK_INTERVAL = 20      # 비활성 클라이언트 확인 간격 (초)

async def broadcast_user_count():
    """모든 클라이언트에게 현재 접속자 수를 전송"""
    message = json.dumps({
        "type": "user_count",
        "count": len(active_users),
        #"max_users": MAX_CONNECTIONS,
        "users": [
            {
            "user_id": user["user_id"]
            } for user in active_users.values()
        ]
    })
    await asyncio.gather(*[ws.send(message) for ws in all_clients if ws.close_code is None])

async def websocket_handler(websocket, path=""):
    """WebSocket 클라이언트 연결을 처리"""
    all_clients.add(websocket)
    sid = id(websocket) # WebSocket 연결마다 고유한 ID 할당
    logging.info(f"✅ WebSocket 클라이언트 연결됨 (SID: {sid})")
    print(f"✅ WebSocket 클라이언트 연결됨 (SID: {sid})")
    
    try:
        await websocket.send(json.dumps({
            "type": "user_count",
            "count": len(active_users),
            "users": [
                {
                "user_id": user["user_id"]
                } for user in active_users.values()
            ]
        }))
        
        while True:
            message = await websocket.recv()
            data = json.loads(message)           
            
            if data.get("type") == "verify_user_exists":    # 이미 존재하는 사용자가 있는 지 확인인
                user_id = data.get("user_id").lower()
                
                existing_sid = next((sid for sid, user in active_users.items() if user["user_id"].lower() == user_id), None)
                if existing_sid is not None:                                 
                    existing_wetsocket = next((ws for ws in all_clients if id(ws) == existing_sid), None)
                    if existing_wetsocket:
                        await existing_wetsocket.send(json.dumps({
                            "type": "duplicate_login",
                            "message": "🚫 다른 장치에서 로그인하여 연결이 해제됩니다."
                        }))                                           
                    continue
                else:
                    await websocket.send(json.dumps({
                        "type": "no_user_active"
                    }))                      
                continue
            
            elif data.get("type") == "add_user":    # 사용자 추가
                user_id = data.get("user_id")  
                token = data.get("token")                       
                logging.info(f"👤 사용자 추가: {user_id} (SID: {sid})")
                print(f"👤 사용자 추가: {user_id} (SID: {sid})")
                        
                active_users[sid] = {
                    "user_id": user_id,
                    "ip": websocket.remote_address[0],
                    "last_active": time.time(),
                    "token": token
                }
                logging.info(f"👤 현재 접속자 수: {len(active_users)}")
                print(f"👤 현재 접속자 수: {len(active_users)}")
                
                await broadcast_user_count()
                
            elif data.get("type") == "pong":    # 클라이언트 PONG 메시지 수신
                if sid in active_users:
                    active_users[sid]["last_active"] = time.time()
                    #print(f"👤 클라이언트 PONG 메시지 수신 (SID: {sid})")
            
            elif data.get("type") == "close":   # 클라이언트 연결 해제 요청
                logging.info(f"❌ 클라이언트 연결 해제 요청 (SID: {sid})")
                active_users[sid]["logout"] = 1  # 로그아웃 처리
                print(f"👤 현재 접속자 수: {len(active_users)}")                
    
    except websockets.exceptions.ConnectionClosedOK:
        logging.info(f"❌ WebSocket 클라이언트 연결 해제됨(ConnectionClosedOK): {sid}")            
        await websocket.close()
        if websocket.close_code is not None:
            logging.info(f"❌ WebSocket 클라이언트 연결 해제 코드: {websocket.close_code}")        
    except websockets.exceptions.ConnectionClosed:
        logging.error(f"❌ WebSocket 클라이언트 연결 해제됨: {sid}")
        print(f"❌ WebSocket 클라이언트 연결 해제됨: {sid}")
        pass
    finally:
        all_clients.remove(websocket)
        if sid in active_users:
            logging.info(f"❌ 클라이언트 연결 해제 finally: {sid}")
            if "logout" not in active_users[sid]:
                # 클라이언트가 비정상 종료한 경우 API 호출
                headers = {"Authorization":f"Bearer {active_users[sid]['token']}"}
                response = requests.get("http://172.16.10.191:20000/user/logout", headers=headers)
                if response.status_code == 200:
                    logging.info(f"❌ 클라이언트 연결 해제(비정상 종료) API 호출 성공: {sid}")
                else:
                    logging.error(f"❌ 클라이언트 연결 해제(비정상 종료) API 호출 실패: {sid}")
            del active_users[sid]
            await broadcast_user_count()

                                      
async def start_websocket_server():
    """WebSocket 서버 실행"""
    server = await websockets.serve(websocket_handler,"0.0.0.0",2002, max_size=2**20, max_queue=32, ping_interval=10, ping_timeout=20, backlog=100)   
    
    logging.info("🚀 WebSocket 서버가 2002번 포트에서 실행 중...")
    print("🚀 WebSocket 서버가 2002번 포트에서 실행 중...")
    
    await server.wait_closed()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_websocket_server())
    loop.run_forever()
    #asyncio.run(start_websocket_server())
