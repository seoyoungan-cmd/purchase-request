from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

SERVER_VERSION = str(int(time.time()))

@app.after_request
def no_cache(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

SLACK_TOKEN = os.environ.get('SLACK_BOT_TOKEN', '')
SLACK_CHANNEL_ID = 'C08CAMBQR6Y'  # 제1원외탕전_총무

REQUESTER_SLACK_IDS = {
    '강대헌': 'U08CD9M4D7D',
    '강진수': 'U0A0R9MRGV9',
    '곽창원': 'U08F849KLSV',
    '구본일': 'U08C89D9Q58',
    '김경화': 'U09M5E55SNT',
    '김광숙': 'U08CD9M3CCT',
    '김남희': 'U0AUQAYHQ5C',
    '김동빈': 'U08BT9K1142',
    '김동효': 'U0AML0UDJE4',
    '김민경': 'U08CD9M5P5Z',
    '김민숙': 'U09KWKV2L15',
    '김보미': 'U08CAQWJPPW',
    '김소윤': 'U097N6HUDHD',
    '김순덕': 'U09L8KSGP1B',
    '김영진': 'U08D26NTBJ4',
    '김영효': 'U08C60H9BU1',
    '김인혜': 'U08CS33A2AV',
    '김현숙': 'U08CDC4244A',
    '김현영': 'U08CS33NHAM',
    '류재현': 'U08BCPB7XMM',
    '문금신': 'U08CDC3LT1Q',
    '문미정': 'U08C6P8ELUE',
    '박나영': 'U09AKF7CXHN',
    '박성배': 'U099ENKJ2BZ',
    '박용근': 'U091R9EL0AE',
    '박정현': 'U0AAZ60K3BN',
    '박지영': 'U08CD9MA1DZ',
    '박현미': 'U08D26P2R88',
    '박현숙': 'U08CFTN7W4U',
    '변석남': 'U09PVPVAD71',
    '서영찬': 'U09ERKR58MD',
    '안서영': 'U09L8PX7LF8',
    '유귀비': 'U08CFTMAYFN',
    '유소은': 'U0AAZ5Z803E',
    '유영옥': 'U08CFTMF9C4',
    '유현경': 'U08D26NQZDW',
    '이다인': 'U09LY84BU4X',
    '이두석': 'U08C64WF3HP',
    '이동규': 'U09NYEYH945',
    '이세라': 'U09BB3Y20KU',
    '이신규': 'U0B06Q5E33J',
    '이종봉': 'U0984HV6BLL',
    '이진경': 'U08CDC3T01Y',
    '이호승': 'U09GK8XPWLU',
    '장순희': 'U09A1JRJY4U',
    '정신우': 'U08U5GLRV8U',
    '정일진': 'U08J8GFM8V8',
    '정재훈': 'U08CZ3VTDEU',
    '정진국': 'U09R3Q23XL2',
    '정진희': 'U08D26P72JC',
    '정희범': 'U08BVR2HANQ',
    '조유정': 'U09RV6NFNAW',
    '주화영': 'U08CFTME56G',
    '진선이': 'U08CD9M25MZ',
    '최선주': 'U0962SFST89',
    '최은영': 'U0947T273LN',
    '하윤하': 'U08BYRVRBTR',
    '하정하': 'U0AQ35Q22HK',
    '하태경': 'U08CDC3U79Q',
    '한탁균': 'U09DZBNU4GM',
    '허라인': 'U08CAQW8Z9S',
}

_avatar_cache = {}

def get_user_avatar(slack_id):
    if not slack_id:
        return None
    if slack_id in _avatar_cache:
        return _avatar_cache[slack_id]
    headers = {'Authorization': f'Bearer {SLACK_TOKEN}'}
    resp = requests.get(
        'https://slack.com/api/users.info',
        headers=headers,
        params={'user': slack_id},
        timeout=10,
    )
    data = resp.json()
    if data.get('ok'):
        url = data.get('user', {}).get('profile', {}).get('image_72', '')
        _avatar_cache[slack_id] = url
        return url or None
    return None


def get_workflow_ts():
    """오늘 '구매 요청' 워크플로 메시지의 ts 반환"""
    if not SLACK_TOKEN:
        return None

    from datetime import date, datetime, timezone, timedelta
    KST = timezone(timedelta(hours=9))
    today = datetime.now(KST).date()
    oldest = datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=KST).timestamp()
    latest = datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=KST).timestamp()

    headers = {'Authorization': f'Bearer {SLACK_TOKEN}'}
    resp = requests.get(
        'https://slack.com/api/conversations.history',
        headers=headers,
        params={
            'channel': SLACK_CHANNEL_ID,
            'oldest': str(oldest),
            'latest': str(latest),
            'limit': 50,
        },
        timeout=10,
    )
    data = resp.json()
    if not data.get('ok'):
        return None

    for msg in data.get('messages', []):
        # workflow_id가 있는 메시지만 대상 (워크플로 메시지 확실히 구분)
        if not msg.get('workflow_id'):
            continue
        username = msg.get('username', '')
        if '구매' in username:
            return msg.get('ts')
    return None


def post_slack_message(text, thread_ts=None, icon_url=None):
    headers = {
        'Authorization': f'Bearer {SLACK_TOKEN}',
        'Content-Type': 'application/json; charset=utf-8',
    }
    payload = {
        'channel': SLACK_CHANNEL_ID,
        'text': text,
        'username': '일호점비서',
    }
    if icon_url:
        payload['icon_url'] = icon_url
    if thread_ts:
        payload['thread_ts'] = thread_ts
    resp = requests.post(
        'https://slack.com/api/chat.postMessage',
        headers=headers,
        json=payload,
        timeout=10,
    )
    return resp.json()


def upload_slack_file(file_content, filename, file_size, channel_id, thread_ts=None, comment=''):
    """Slack 최신 방식으로 파일 업로드 (getUploadURLExternal)"""
    headers = {'Authorization': f'Bearer {SLACK_TOKEN}'}

    # 1단계: 업로드 URL 획득
    resp = requests.get(
        'https://slack.com/api/files.getUploadURLExternal',
        headers=headers,
        params={'filename': filename, 'length': file_size},
        timeout=10,
    )
    data = resp.json()
    if not data.get('ok'):
        return data

    upload_url = data['upload_url']
    file_id = data['file_id']

    # 2단계: 파일 업로드
    requests.post(upload_url, data=file_content, timeout=30)

    # 3단계: 업로드 완료 처리
    complete_payload = {
        'files': [{'id': file_id, 'title': filename}],
        'channel_id': channel_id,
    }
    if thread_ts:
        complete_payload['thread_ts'] = thread_ts
    if comment:
        complete_payload['initial_comment'] = comment

    complete_resp = requests.post(
        'https://slack.com/api/files.completeUploadExternal',
        headers={**headers, 'Content-Type': 'application/json; charset=utf-8'},
        json=complete_payload,
        timeout=10,
    )
    return complete_resp.json()


@app.route('/ping')
def ping():
    return jsonify({'ok': True})


@app.route('/api/version')
def api_version():
    return jsonify({'version': SERVER_VERSION})


@app.route('/')
def index():
    return render_template('index.html', server_version=SERVER_VERSION)


@app.route('/api/submit', methods=['POST'])
def submit():
    data_str = request.form.get('data', '{}')
    try:
        data = json.loads(data_str)
    except Exception:
        return jsonify({'success': False, 'error': '잘못된 데이터 형식입니다.'})

    requester = (data.get('requester') or '').strip()
    dept      = (data.get('dept') or '').strip()
    items     = data.get('items', [])

    if not requester:
        return jsonify({'success': False, 'error': '요청자 이름을 입력해주세요.'})
    if not items:
        return jsonify({'success': False, 'error': '품목을 1개 이상 입력해주세요.'})
    if not SLACK_TOKEN:
        return jsonify({'success': False, 'error': 'SLACK_BOT_TOKEN이 설정되지 않았습니다.'})

    # 메시지 구성
    sender = f'{dept} {requester}'.strip() if dept else requester
    lines = [f'🛒 *{sender}* 님의 구매 요청', '']

    전결 = [item for item in items if (item.get('category') or '').strip() == '전결']
    일반 = [item for item in items if (item.get('category') or '').strip() != '전결']

    def format_item(num, item):
        product = (item.get('product') or '').strip()
        quantity = item.get('quantity', 1)
        reason = (item.get('reason') or '').strip()
        has_photo = item.get('has_photo', False)
        option = (item.get('option') or '').strip()
        link = (item.get('link') or '').strip()
        price = (item.get('price') or '').strip()
        product_display = f'{product} ({option})' if option else product
        result = [f'*{num}. {product_display}*',
                  f'   · 수량: {quantity}개',
                  f'   · 요청 이유: {reason}']
        if link:
            result.append(f'   · 구매링크: <{link}|링크>')
        if price:
            result.append(f'   · 가격: {price}')
        if has_photo:
            result.append('   · 📷 사진 첨부됨')
        return result

    num = 1
    일반_with_nums = []

    if 전결:
        lines.append('✅ *전결* (즉시 구매)')
        for item in 전결:
            lines.extend(format_item(num, item))
            num += 1
            lines.append('')
    if 일반:
        lines.append('📋 *일반* (품의 필요)')
        for item in 일반:
            lines.extend(format_item(num, item))
            일반_with_nums.append((num, item))
            num += 1
            lines.append('')
    if lines and lines[-1] == '':
        lines.pop()

    # 품의 양식 블록
    if 일반:
        lines.append('')
        lines.append('───────────────────')
        lines.append('📋 *품의 양식* (복사 후 품의 채널에 붙여넣기)')
        for item_num, item in 일반_with_nums:
            product     = (item.get('product') or '').strip()
            option      = (item.get('option') or '').strip()
            quantity    = item.get('quantity', 1)
            reason      = (item.get('reason') or '').strip()
            link        = (item.get('link') or '').strip()
            price       = (item.get('price') or '').strip()
            product_display    = f'{product} ({option})' if option else product
            quantity_display   = f'{option} {quantity}개' if option else f'{quantity}개'
            price_display      = price if price else '-'
            procurement_source = f'네이버({product_display})' if link else '-'
            lines.append('')
            if len(일반) > 1:
                lines.append(f'*[{item_num}번 품목]*')
            lines.append(f'• 구입 주체 : 산청1호점')
            lines.append(f'• 구매 품목 : {product_display}')
            lines.append(f'• 구매 금액 : {price_display}')
            lines.append(f'• 구매 수량 : {quantity_display}')
            lines.append(f'• 구매처명 : {procurement_source}')
            lines.append(f'• 구매 사유 : {reason}')

    message_text = '\n'.join(lines)
    thread_ts = get_workflow_ts()
    slack_id = REQUESTER_SLACK_IDS.get(requester, '')
    icon_url = get_user_avatar(slack_id) if slack_id else None
    result = post_slack_message(message_text, thread_ts, icon_url=icon_url)

    if not result.get('ok'):
        return jsonify({'success': False, 'error': result.get('error', '슬랙 전송 실패')})

    msg_ts = result.get('ts')

    # 사진 파일 업로드 (스레드에 첨부)
    photo_errors = []
    for i, item in enumerate(items):
        file_key = f'photo_{i}'
        if file_key not in request.files:
            continue
        file = request.files[file_key]
        if not file or not file.filename:
            continue

        product = (item.get('product') or f'품목 {i+1}').strip()
        file_content = file.read()
        up_result = upload_slack_file(
            file_content,
            file.filename,
            len(file_content),
            SLACK_CHANNEL_ID,
            thread_ts=msg_ts,
            comment=f'📷 {product} 첨부 사진',
        )
        if not up_result.get('ok'):
            photo_errors.append(f'{product}: {up_result.get("error", "업로드 실패")}')

    no_workflow = '' if thread_ts else ' (오늘 구매 요청 워크플로를 찾지 못해 채널에 새 메시지로 전송됐습니다.)'

    if photo_errors:
        return jsonify({
            'success': True,
            'notice': f'요청이 전송됐으나 사진 업로드 일부 실패: {", ".join(photo_errors)}{no_workflow}'
        })

    return jsonify({'success': True, 'notice': no_workflow or None})


ADMIN_PASSWORD = '1004'


@app.route('/api/admin/messages', methods=['GET'])
def admin_messages():
    if request.args.get('password', '') != ADMIN_PASSWORD:
        return jsonify({'success': False, 'error': '비밀번호가 틀렸습니다.'})

    from datetime import date, datetime, timezone, timedelta
    KST = timezone(timedelta(hours=9))
    today = datetime.now(KST).date()
    oldest = datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=KST).timestamp()
    latest = datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=KST).timestamp()

    headers = {'Authorization': f'Bearer {SLACK_TOKEN}'}

    def extract_requester(text):
        import re
        m = re.search(r'\*(.+?)\* 님의 구매 요청', text)
        return m.group(1) if m else ''

    bot_messages = []

    # 1) 채널 직접 메시지
    resp = requests.get(
        'https://slack.com/api/conversations.history',
        headers=headers,
        params={'channel': SLACK_CHANNEL_ID, 'oldest': str(oldest), 'latest': str(latest), 'limit': 100},
        timeout=10,
    )
    data = resp.json()
    if data.get('ok'):
        for msg in data.get('messages', []):
            text = msg.get('text', '')
            is_bot = msg.get('bot_id') or msg.get('subtype') == 'bot_message'
            if is_bot and '구매 요청' in text and not msg.get('workflow_id'):
                bot_messages.append({
                    'ts': msg.get('ts'),
                    'preview': text.split('\n')[0][:50],
                    'requester': extract_requester(text),
                })

    # 2) 워크플로 스레드 내 댓글
    thread_ts = get_workflow_ts()
    if thread_ts:
        reply_resp = requests.get(
            'https://slack.com/api/conversations.replies',
            headers=headers,
            params={'channel': SLACK_CHANNEL_ID, 'ts': thread_ts, 'limit': 200},
            timeout=10,
        )
        reply_data = reply_resp.json()
        for msg in reply_data.get('messages', []):
            if msg.get('ts') == thread_ts:
                continue
            text = msg.get('text', '')
            is_bot = msg.get('bot_id') or msg.get('subtype') == 'bot_message'
            if is_bot and '구매 요청' in text:
                bot_messages.append({
                    'ts': msg.get('ts'),
                    'preview': text.split('\n')[0][:50],
                    'requester': extract_requester(text),
                })

    return jsonify({'success': True, 'messages': bot_messages})


@app.route('/api/admin/delete', methods=['POST'])
def admin_delete():
    data = request.get_json()
    if data.get('password', '') != ADMIN_PASSWORD:
        return jsonify({'success': False, 'error': '비밀번호가 틀렸습니다.'})

    ts = data.get('ts', '')
    if not ts:
        return jsonify({'success': False, 'error': 'ts 값이 없습니다.'})

    headers = {'Authorization': f'Bearer {SLACK_TOKEN}', 'Content-Type': 'application/json; charset=utf-8'}
    resp = requests.post(
        'https://slack.com/api/chat.delete',
        headers=headers,
        json={'channel': SLACK_CHANNEL_ID, 'ts': ts},
        timeout=10,
    )
    result = resp.json()
    if result.get('ok'):
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': result.get('error', '삭제 실패')})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
