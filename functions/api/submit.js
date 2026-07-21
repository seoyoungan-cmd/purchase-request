const SLACK_CHANNEL_ID = 'C08CAMBQR6Y'; // 제1원외탕전_총무
const ADMIN_SLACK_ID  = 'U09L8PX7LF8'; // 안서영 (품의 양식 DM 수신)
const RYJH_SLACK_ID   = 'U08BCPB7XMM'; // 류재현

const REQUESTER_SLACK_IDS = {
  '문금신': 'U08CDC3LT1Q',
  '김경화': 'U09M5E55SNT',
  '박나영': 'U09AKF7CXHN',
  '안서영': 'U09L8PX7LF8',
  '이진경': 'U08CDC3T01Y',
  '조유정': 'U09RV6NFNAW',
  '주화영': 'U08CFTME56G',
  '하태경': 'U08CDC3U79Q',
  '허라인': 'U08CAQW8Z9S',
  '류재현': 'U08BCPB7XMM',
  '정진국': 'U09R3Q23XL2',
  '강진수': 'U0A0R9MRGV9',
  '김남희': 'U0AUQAYHQ5C',
  '박지영': 'U08CD9MA1DZ',
};

function kstMidnight() {
  const KST = 9 * 3600;
  const now = Math.floor(Date.now() / 1000) + KST;
  return now - (now % 86400); // UTC 자정 기준 KST 00:00
}

async function getWorkflowTs(token) {
  const oldest = kstMidnight() - 9 * 3600;
  const latest = oldest + 86399;
  const resp = await fetch(
    `https://slack.com/api/conversations.history?channel=${SLACK_CHANNEL_ID}&oldest=${oldest}&latest=${latest}&limit=50`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  const data = await resp.json();
  if (!data.ok) return null;
  for (const msg of data.messages || []) {
    if (!msg.workflow_id) continue;
    if ((msg.username || '').includes('구매')) return msg.ts;
  }
  return null;
}

async function postSlackMessage(token, text, threadTs, iconUrl) {
  const payload = { channel: SLACK_CHANNEL_ID, text, username: '일호점비서' };
  if (threadTs) payload.thread_ts = threadTs;
  if (iconUrl)  payload.icon_url  = iconUrl;
  const resp = await fetch('https://slack.com/api/chat.postMessage', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json; charset=utf-8' },
    body: JSON.stringify(payload),
  });
  return resp.json();
}

async function sendDM(token, userId, text) {
  const openResp = await fetch('https://slack.com/api/conversations.open', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json; charset=utf-8' },
    body: JSON.stringify({ users: userId }),
  });
  const openData = await openResp.json();
  if (!openData.ok) return openData;
  const resp = await fetch('https://slack.com/api/chat.postMessage', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json; charset=utf-8' },
    body: JSON.stringify({ channel: openData.channel.id, text }),
  });
  return resp.json();
}

async function getUserAvatar(token, userId) {
  if (!userId) return null;
  try {
    const resp = await fetch(`https://slack.com/api/users.info?user=${userId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    const data = await resp.json();
    return data.user?.profile?.image_72 || null;
  } catch { return null; }
}

async function uploadSlackFile(token, fileContent, filename, channelId, threadTs, comment) {
  const urlResp = await fetch('https://slack.com/api/files.getUploadURLExternal', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename, length: fileContent.byteLength }),
  });
  const urlData = await urlResp.json();
  if (!urlData.ok) return urlData;

  await fetch(urlData.upload_url, { method: 'POST', body: fileContent });

  const completeResp = await fetch('https://slack.com/api/files.completeUploadExternal', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      files: [{ id: urlData.file_id }],
      channel_id: channelId,
      thread_ts: threadTs,
      initial_comment: comment,
    }),
  });
  return completeResp.json();
}

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

export async function onRequestPost(context) {
  const { request, env } = context;
  const SLACK_TOKEN = env.SLACK_BOT_TOKEN;
  if (!SLACK_TOKEN) return json({ success: false, error: 'SLACK_BOT_TOKEN이 설정되지 않았습니다.' });

  let formData;
  try { formData = await request.formData(); }
  catch { return json({ success: false, error: '데이터 파싱 오류' }); }

  let data;
  try { data = JSON.parse(formData.get('data') || '{}'); }
  catch { return json({ success: false, error: '잘못된 데이터 형식입니다.' }); }

  const requester = (data.requester || '').trim();
  const dept      = (data.dept || '').trim();
  const items     = data.items || [];

  if (!requester) return json({ success: false, error: '요청자 이름을 입력해주세요.' });
  if (!items.length) return json({ success: false, error: '품목을 1개 이상 입력해주세요.' });

  // ── 슬랙 메시지 구성 ─────────────────────────────────
  const sender = dept ? `${dept} ${requester}` : requester;
  const lines = [`🛒 *${sender}* 님의 구매 요청`, ''];

  const 전결 = items.filter(it => (it.category || '').trim() === '전결');
  const 일반 = items.filter(it => (it.category || '').trim() !== '전결');

  function formatItem(num, item) {
    const product  = (item.product || '').trim();
    const option   = (item.option  || '').trim();
    const quantity = item.quantity || 1;
    const reason   = (item.reason  || '').trim();
    const link     = (item.link    || '').trim();
    const price    = (item.price   || '').trim();
    const display  = option ? `${product} (${option})` : product;
    const result   = [`*${num}. ${display}*`, `   · 수량: ${quantity}개`, `   · 요청 이유: ${reason}`];
    if (link)           result.push(`   · 구매링크: <${link}|링크>`);
    if (price)          result.push(`   · 가격: ${price}`);
    if (item.has_photo) result.push('   · 📷 사진 첨부됨');
    return result;
  }

  let num = 1;
  const 일반WithNums = [];

  if (전결.length) {
    lines.push('✅ *전결* (즉시 구매)');
    for (const item of 전결) { lines.push(...formatItem(num, item)); num++; lines.push(''); }
  }
  if (일반.length) {
    lines.push('📋 *일반* (품의 필요)');
    for (const item of 일반) {
      lines.push(...formatItem(num, item));
      일반WithNums.push([num, item]);
      num++;
      lines.push('');
    }
  }
  if (lines[lines.length - 1] === '') lines.pop();

  // ── 슬랙 채널 전송 ───────────────────────────────────
  const threadTs = await getWorkflowTs(SLACK_TOKEN);
  const slackId  = REQUESTER_SLACK_IDS[requester] || '';
  const iconUrl  = await getUserAvatar(SLACK_TOKEN, slackId);
  const result   = await postSlackMessage(SLACK_TOKEN, lines.join('\n'), threadTs, iconUrl);

  if (!result.ok) return json({ success: false, error: result.error || '슬랙 전송 실패' });

  const msgTs = result.ts;

  // ── 사진 업로드 ──────────────────────────────────────
  const photoErrors = [];
  for (let i = 0; i < items.length; i++) {
    const file = formData.get(`photo_${i}`);
    if (!file || typeof file === 'string') continue;
    const product  = (items[i].product || `품목 ${i + 1}`).trim();
    const content  = await file.arrayBuffer();
    const upResult = await uploadSlackFile(
      SLACK_TOKEN, content, file.name || `photo_${i}.jpg`,
      SLACK_CHANNEL_ID, msgTs, `📷 ${product} 첨부 사진`
    );
    if (!upResult.ok) photoErrors.push(`${product}: ${upResult.error || '업로드 실패'}`);
  }

  // ── 품의 양식 DM ─────────────────────────────────────
  if (일반WithNums.length) {
    const dm = ['📋 *품의 양식*', ''];
    for (const [itemNum, item] of 일반WithNums) {
      const product  = (item.product || '').trim();
      const option   = (item.option  || '').trim();
      const quantity = item.quantity || 1;
      const reason   = (item.reason  || '').trim();
      const link     = (item.link    || '').trim();
      const price    = (item.price   || '').trim();
      const display  = option ? `${product} (${option})` : product;
      const qtyDisp  = option ? `${option} ${quantity}개` : `${quantity}개`;

      if (일반WithNums.length > 1) dm.push(`*[${itemNum}번 품목]*`);
      dm.push(`<@${RYJH_SLACK_ID}>`);
      dm.push(`• 구입 주체 : 산청1호점`);
      dm.push(`• 구매 품목 : ${display}`);
      dm.push(`• 구매 금액 : ${price || '-'}`);
      dm.push(`• 구매 수량 : ${qtyDisp}`);
      dm.push(`• 구매처명 : ${link ? '네이버' : '-'}`);
      dm.push(`• 구매 사유 : ${reason}`);
      if (일반WithNums.length > 1) dm.push('');
    }
    await sendDM(SLACK_TOKEN, ADMIN_SLACK_ID, dm.join('\n'));
  }

  const noWorkflow = threadTs ? null : '오늘 구매 요청 워크플로를 찾지 못해 채널에 새 메시지로 전송됐습니다.';
  const notice = photoErrors.length
    ? `사진 업로드 일부 실패: ${photoErrors.join(', ')}${noWorkflow ? ' / ' + noWorkflow : ''}`
    : noWorkflow;

  return json({ success: true, notice });
}
