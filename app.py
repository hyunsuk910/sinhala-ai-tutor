# app.py
import os
import json
import uuid
import re
import random
import hashlib
import base64
from datetime import datetime
import streamlit as st
from google import genai
from google.genai import types
from gtts import gTTS
from prompts import get_lesson_prompt, get_tutor_prompt

# ==========================================
# 1. 전역 설정 및 모바일/태블릿 반응형 CSS
# ==========================================
MODEL_ID = "gemini-3.8-flash"
DATA_FILE = "local_storage.json"
AUDIO_DIR = "audio_cache"

os.makedirs(AUDIO_DIR, exist_ok=True)

st.set_page_config(
    page_title="싱할라어 AI 튜터",
    page_icon="🇱🇰",
    layout="wide",
    initial_sidebar_state="collapsed"  # 모바일에서 메인 컨텐츠를 먼저 보여주도록 기본 접힘 설정
)

st.markdown("""
<style>
    /* 기본 모바일 여백 및 레이아웃 최적화 */
    .block-container {
        padding-top: 1.8rem !important;
        padding-bottom: 6rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }

    /* 1) 싱할라 문자 반응형 크기 조절 (화면폭에 맞춰 자동 스케일링) */
    code {
        font-size: 0.95rem !important;
    }
    .si-char {
        font-size: clamp(1.8rem, 4.5vw, 2.3rem) !important;
        font-weight: 700 !important;
        color: #60a5fa !important;
        line-height: 1.65 !important;
        padding: 0 4px;
        font-family: "Noto Sans Sinhala", "Iskoola Pota", sans-serif;
    }
    .si-char-xl {
        font-size: clamp(2.3rem, 6vw, 3.1rem) !important;
        font-weight: 800 !important;
        color: #60a5fa !important;
        line-height: 1.5 !important;
    }

    /* 2) 텍스트 스타일 */
    .ko-meaning {
        font-size: clamp(1.15rem, 3.5vw, 1.4rem) !important;
        font-weight: 800 !important;
        color: inherit !important;
    }
    .ko-meaning-xl {
        font-size: clamp(1.8rem, 5vw, 2.4rem) !important;
        font-weight: 800 !important;
        color: #f8fafc !important;
        margin: 16px 0 !important;
    }
    .ko-pronun {
        font-size: clamp(1.25rem, 3.8vw, 1.6rem) !important;
        font-weight: 700 !important;
        color: #fbbf24 !important;
        margin-top: 10px !important;
    }

    /* 3) 플래시카드 모바일 카드 디자인 */
    .flashcard {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 2px solid #334155;
        border-radius: 20px;
        padding: 28px 16px;
        text-align: center;
        box-shadow: 0 8px 24px rgba(0,0,0,0.25);
        margin-bottom: 16px;
        color: #f8fafc !important;
    }
    .flashcard-sub {
        color: #94a3b8 !important;
        font-size: 0.95rem !important;
        margin-bottom: 8px !important;
    }

    /* 4) 상단 소제목 바로가기: 모바일 앱 스타일 가로 스와이프 칩 바 */
    .toc-scroll-wrapper {
        display: flex;
        overflow-x: auto;
        white-space: nowrap;
        gap: 8px;
        padding: 10px 4px;
        margin-bottom: 16px;
        -webkit-overflow-scrolling: touch;
    }
    .toc-scroll-wrapper::-webkit-scrollbar {
        display: none;
    }
    .toc-chip {
        display: inline-block;
        text-decoration: none !important;
        padding: 8px 16px;
        border-radius: 24px;
        background: #2563eb;
        color: #ffffff !important;
        font-weight: 700;
        font-size: 0.88rem;
        flex-shrink: 0;
        box-shadow: 0 2px 6px rgba(0,0,0,0.15);
    }
    .toc-chip:active {
        background: #1d4ed8;
        transform: scale(0.96);
    }

    /* 5) 오디오 위젯 & 모바일 전용 플로팅 녹음 버튼 */
    div[data-testid="stAudioInput"] {
        background: rgba(30, 41, 59, 0.95) !important;
        border: 2px solid #475569 !important;
        border-radius: 18px !important;
        padding: 12px 14px !important;
        margin: 10px 0 !important;
    }
    div[data-testid="stAudioInput"] button {
        width: 44px !important;
        height: 44px !important;
        min-width: 44px !important;
        min-height: 44px !important;
        border-radius: 50% !important;
        transform: none !important;
        margin: 4px !important;
    }
    /* 플로팅 녹음 버튼: 모바일 내비게이션 바 위쪽에 배치 */
    div[data-testid="stAudioInput"] button:first-of-type {
        position: fixed !important;
        bottom: 24px !important;
        right: 20px !important;
        width: 72px !important;
        height: 72px !important;
        min-width: 72px !important;
        min-height: 72px !important;
        border-radius: 50% !important;
        background: radial-gradient(circle, #ff4b4b 0%, #dc2626 100%) !important;
        border: 3px solid #ffffff !important;
        color: #ffffff !important;
        box-shadow: 0 6px 20px rgba(239, 68, 68, 0.75) !important;
        z-index: 999999 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    div[data-testid="stAudioInput"] button:first-of-type svg {
        width: 32px !important;
        height: 32px !important;
        fill: #ffffff !important;
    }

    /* 6) 모바일 화면 반응형 스택 레이아웃 처리 */
    @media (max-width: 768px) {
        /* 모바일에서는 버튼 터치 히트박스를 키우고 간격 확보 */
        .stButton button {
            min-height: 48px !important;
            font-size: 1rem !important;
            font-weight: 700 !important;
        }
        audio {
            height: 44px !important;
        }
    }
    /* ==========================================
       Gemini / ChatGPT 스타일 사이드바 CSS
       ========================================== */
    section[data-testid="stSidebar"] {
        background-color: #131314 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    }
    section[data-testid="stSidebar"] .block-container {
        padding: 1.2rem 0.8rem !important;
    }

    /* 상단 로고 & 브랜딩 */
    .sidebar-brand {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 4px 8px 16px 8px;
        font-size: 1.15rem;
        font-weight: 700;
        color: #e3e3e3;
        letter-spacing: -0.3px;
    }

    /* Gemini 스타일 타원형 '+ 새 학습' 버튼 */
    .stSidebar div[data-testid="stButton"] button[kind="primary"] {
        background: #1e1f20 !important;
        color: #e3e3e3 !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 28px !important;
        padding: 0.65rem 1.2rem !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2) !important;
        transition: all 0.2s cubic-bezier(0.2, 0, 0, 1) !important;
        text-align: left !important;
        display: flex !important;
        justify-content: flex-start !important;
    }
    .stSidebar div[data-testid="stButton"] button[kind="primary"]:hover {
        background: #282a2c !important;
        border-color: rgba(255, 255, 255, 0.25) !important;
        transform: translateY(-1px);
    }

    /* 최근 대화/학습 리스트 버튼 */
    .sidebar-history-item {
        margin-bottom: 2px;
    }
    .stSidebar div[data-testid="stButton"] button[kind="secondary"] {
        background: transparent !important;
        color: #c4c7c5 !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.55rem 0.85rem !important;
        font-size: 0.9rem !important;
        font-weight: 500 !important;
        text-align: left !important;
        justify-content: flex-start !important;
        overflow: hidden !important;
        white-space: nowrap !important;
        text-overflow: ellipsis !important;
        transition: background 0.15s ease !important;
    }
    .stSidebar div[data-testid="stButton"] button[kind="secondary"]:hover {
        background: #1e1f20 !important;
        color: #e3e3e3 !important;
    }

    /* 현재 활성화된 세션 아이템 */
    .stSidebar div[data-testid="stButton"] button[kind="primary"].active-session {
        background: rgba(68, 71, 79, 0.5) !important;
        color: #a8c7fa !important;
        border: 1px solid rgba(168, 199, 250, 0.3) !important;
    }

    /* 카테고리 헤더 */
    .sidebar-section-title {
        font-size: 0.75rem;
        font-weight: 700;
        color: #8e918f;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        padding: 16px 8px 6px 8px;
    }

    /* 사이드바 하단 환경설정 접기 박스 */
    .stSidebar div[data-testid="stExpander"] {
        background: transparent !important;
        border: none !important;
        border-top: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 0 !important;
        padding-top: 8px !important;
    }
    .stSidebar div[data-testid="stExpander"] details summary {
        color: #8e918f !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
    }
</style>
""", unsafe_allow_html=True)

# PWA 메타 태그 (1회만 추가)
st.markdown("""
<link rel="manifest" href="/app/static/manifest.json">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#131314">
""", unsafe_allow_html=True)
# ==========================================
# 2. 헬퍼 함수
# ==========================================
def enlarge_sinhala_only(text: str) -> str:
    if not text:
        return ""
    return re.sub(
        r'([\u0D80-\u0DFF]+(?:\s+[\u0D80-\u0DFF]+)*)',
        r'<span class="si-char">\1</span>',
        text
    )

def inject_section_anchors(content: str) -> str:
    lines = content.splitlines()
    out = []
    for line in lines:
        if line.startswith("## "):
            if "핵심 표현" in line:
                out.append('<div id="sec-expr"></div>')
            elif "이메일" in line or "대화문" in line or "독해" in line:
                out.append('<div id="sec-read"></div>')
            elif "핵심 단어장" in line or "단어장" in line:
                out.append('<div id="sec-vocab"></div>')
            elif "퀴즈" in line:
                out.append('<div id="sec-quiz"></div>')
        out.append(line)
    return "\n".join(out)

def get_audio_file(text: str, slow: bool = False) -> str:
    if not text:
        return None
    si_matches = re.findall(r'[\u0D80-\u0DFF]+(?:\s+[\u0D80-\u0DFF]+)*', text)
    target_text = " ".join(si_matches).strip() if si_matches else text.strip()
    if not target_text:
        return None

    speed_tag = "slow" if slow else "norm"
    file_hash = hashlib.md5(f"{target_text}_{speed_tag}".encode("utf-8")).hexdigest()
    file_path = os.path.join(AUDIO_DIR, f"{file_hash}.mp3")
    
    if not os.path.exists(file_path):
        try:
            tts = gTTS(text=target_text, lang="si", slow=slow)
            tts.save(file_path)
        except Exception:
            return None
    return file_path

def autoplay_audio(file_path: str):
    if file_path and os.path.exists(file_path):
        with open(file_path, "rb") as f:
            data = f.read()
        b64 = base64.b64encode(data).decode()
        rand_id = str(uuid.uuid4())[:6]
        html = f"""
        <audio id="auto_{rand_id}" autoplay="true" style="display:none;">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
        """
        st.markdown(html, unsafe_allow_html=True)

def clean_md(val: str) -> str:
    if not val:
        return ""
    return re.sub(r'^[\*\-\s`"\']+|[\*\-\s`"\']+$', '', val).strip()

def extract_sentence_blocks(content: str):
    blocks = []
    lines = content.splitlines()
    curr = {}

    for line in lines:
        s = line.strip()
        if s.startswith("##"):
            if curr.get("sinhala"):
                blocks.append(curr)
            curr = {}
            continue

        m_mean = re.search(r"\*\*(?:한국어\s*)?(?:의미|뜻|번역):\*\*\s*(.+)", s)
        m_si = re.search(r"\*\*싱할라어(?:\s*원문)?:\*\*\s*(.+)", s)
        m_pr = re.search(r"\*\*(?:한국어\s*)?발음:\*\*\s*(.+)", s)
        m_map = re.search(r"\*\*🧩\s*1:1\s*어순\s*매칭:\*\*\s*(.+)", s)

        if m_mean:
            if "meaning" in curr and curr.get("sinhala"):
                blocks.append(curr)
                curr = {}
            curr["meaning"] = clean_md(m_mean.group(1))
        elif m_si:
            if "sinhala" in curr:
                blocks.append(curr)
                curr = {}
            curr["sinhala"] = clean_md(m_si.group(1))
        elif m_pr:
            curr["pronun"] = clean_md(m_pr.group(1))
        elif m_map:
            curr["mapping"] = clean_md(m_map.group(1))

    if curr.get("sinhala"):
        blocks.append(curr)

    return blocks

def extract_vocab_table(content: str):
    vocab_list = []
    lines = content.splitlines()
    in_table = False

    for line in lines:
        s = line.strip()
        if s.startswith("|") and s.endswith("|"):
            cells = [clean_md(c) for c in s.strip("|").split("|")]
            if all(re.match(r"^[-:\s]+$", c) for c in cells if c):
                continue
            if not in_table and any(k in "".join(cells) for k in ["뜻", "의미", "싱할라", "발음", "로마자"]):
                in_table = True
                continue
            if in_table and len(cells) >= 3:
                si_col = -1
                for idx, c in enumerate(cells):
                    if re.search(r'[\u0D80-\u0DFF]', c):
                        si_col = idx
                        break

                if si_col == 0:
                    sinhala = cells[0]
                    pronun = cells[1] if len(cells) > 1 else ""
                    roman = cells[2] if len(cells) > 2 else ""
                    meaning = cells[3] if len(cells) > 3 else cells[1]
                    note = cells[4] if len(cells) > 4 else ""
                else:
                    meaning = cells[0]
                    sinhala = cells[1] if len(cells) > 1 else ""
                    pronun = cells[2] if len(cells) > 2 else ""
                    roman = cells[3] if len(cells) > 3 else ""
                    note = cells[4] if len(cells) > 4 else ""

                full_pronun = f"{pronun} ({roman})" if roman and roman not in pronun else pronun
                if sinhala or meaning:
                    vocab_list.append({
                        "meaning": meaning,
                        "sinhala": sinhala,
                        "pronun": full_pronun,
                        "note": note
                    })
        elif in_table and s.startswith("##"):
            break
    return vocab_list

# ==========================================
# 3. 로컬 영구 저장소
# ==========================================
def is_bad_meaning(val: str) -> bool:
    if not val:
        return True
    bad_keywords = ["주요 문장", "핵심 표현", "본문 주요 표현", "뜻 없음", "의미 미기재", "뜻 미기재"]
    return any(val.endswith(k) or val == k for k in bad_keywords)

def is_bad_pronun(val: str) -> bool:
    if not val:
        return True
    bad_keywords = ["가이드 본문 참조", "본문 발음 참조", "본문 참조", "발음 미기재", "튜터 피드백 참조"]
    return any(k in val for k in bad_keywords)

def load_storage():
    default_structure = {
        "api_key": "",
        "lessons": {},
        "current_lesson_id": None,
        "vocab_notes": []
    }
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for key, val in default_structure.items():
                    if key not in data:
                        data[key] = val
                return data
        except Exception:
            pass
    return default_structure

def save_storage(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_to_vocab(storage, item_dict):
    for existing in storage["vocab_notes"]:
        if existing.get("sinhala") and existing.get("sinhala") == item_dict.get("sinhala"):
            updated = False
            if is_bad_meaning(existing.get("meaning", "")) and not is_bad_meaning(item_dict.get("meaning", "")):
                existing["meaning"] = item_dict["meaning"]
                updated = True
            if is_bad_pronun(existing.get("pronun", "")) and not is_bad_pronun(item_dict.get("pronun", "")):
                existing["pronun"] = item_dict["pronun"]
                updated = True
            if updated:
                save_storage(storage)
                return "updated"
            return "duplicate"
    
    storage["vocab_notes"].append({
        "id": str(uuid.uuid4())[:8],
        "lesson_title": item_dict.get("lesson_title", "맞춤 학습"),
        "type": item_dict.get("type", "단어"),
        "sinhala": item_dict.get("sinhala", ""),
        "pronun": item_dict.get("pronun", ""),
        "meaning": item_dict.get("meaning", ""),
        "note": item_dict.get("note", ""),
        "starred": False,
        "mastered": False,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    save_storage(storage)
    return "added"

if "storage" not in st.session_state:
    st.session_state.storage = load_storage()

storage = st.session_state.storage

if "autoplay_file" not in st.session_state:
    st.session_state.autoplay_file = None

if st.session_state.autoplay_file:
    autoplay_audio(st.session_state.autoplay_file)
    st.session_state.autoplay_file = None

# ==========================================
# 4. 사이드바: Gemini 스타일 미니멀 다크 내비게이션
# ==========================================
with st.sidebar:
    # 1) 상단 브랜드 로고
    st.markdown("""
    <div class="sidebar-brand">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <path d="M12 2L14.5 9.5L22 12L14.5 14.5L12 22L9.5 14.5L2 12L9.5 9.5L12 2Z" fill="url(#gemini-grad)"/>
            <defs>
                <linearGradient id="gemini-grad" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
                    <stop stop-color="#7cacf8"/>
                    <stop offset="0.5" stop-color="#a8c7fa"/>
                    <stop offset="1" stop-color="#4285f4"/>
                </linearGradient>
            </defs>
        </svg>
        <span>Sinhala AI</span>
    </div>
    """, unsafe_allow_html=True)

    # 2) Gemini 시그니처 '+ 새 학습 만들기' 캡슐 버튼
    with st.popover("✨  새 맞춤 학습 생성", use_container_width=True):
        st.markdown("##### 🚀 새 학습 커리큘럼 생성")
        new_topic = st.text_input("학습 주제", placeholder="예: 납기일 조정 이메일, 현지 택시 흥정")
        new_mode = st.selectbox(
            "집중 영역",
            ["비즈니스 이메일(문어체) + 일상 회화(구어체)", "비즈니스 이메일 독해 집중", "일상 생존 회화 집중"]
        )
        new_level = st.selectbox(
            "분량 및 난이도",
            ["핵심 요약 (15분 분량)", "표준 학습 (30분 분량 / 퀴즈 포함)", "심화 마스터 (심층 어순 분석)"]
        )
        if st.button("학습 생성 시작", use_container_width=True, type="primary"):
            if not storage.get("api_key"):
                st.error("하단 설정에서 API Key를 먼저 입력해 주세요.")
            elif not new_topic.strip():
                st.warning("학습 주제를 입력해 주세요.")
            else:
                with st.spinner(f"'{new_topic}' 가이드 생성 중..."):
                    try:
                        client = genai.Client(api_key=storage["api_key"])
                        prompt = get_lesson_prompt(new_topic.strip(), new_mode, new_level)
                        response = client.models.generate_content(
                            model=MODEL_ID,
                            contents=prompt
                        )
                        lesson_id = str(uuid.uuid4())[:8]
                        storage["lessons"][lesson_id] = {
                            "id": lesson_id,
                            "title": new_topic.strip(),
                            "mode": new_mode,
                            "level": new_level,
                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "content": response.text,
                            "chat_history": []
                        }
                        storage["current_lesson_id"] = lesson_id
                        save_storage(storage)
                        st.rerun()
                    except Exception as e:
                        st.error(f"생성 중 오류: {e}")

    # 3) 작업 공간 내비게이션 (Gemini 모드 전환기)
    MENU_OPTIONS = [
        "📑 맞춤 학습 센터",
        "🎙️ 실시간 AI 튜터 (음성 대화방)",
        "📒 통합 단어장 & 퀴즈"
    ]
    app_mode = st.radio(
        "Navigation",
        MENU_OPTIONS,
        label_visibility="collapsed",
        key="main_nav_mode"
    )

    # 4) 최근 히스토리 목록 (Recent Chats)
    st.markdown('<div class="sidebar-section-title">최근 학습 및 대화</div>', unsafe_allow_html=True)

    lessons_dict = storage.get("lessons", {})
    if not lessons_dict:
        st.caption("저장된 내역이 없습니다.")
    else:
        sorted_lessons = sorted(
            lessons_dict.values(),
            key=lambda x: x.get("created_at", ""),
            reverse=True
        )
        for item in sorted_lessons:
            is_selected = (item["id"] == storage.get("current_lesson_id"))
            icon = "🎙️" if item.get("mode") == "음성 대화" else "💬"
            
            # 세션 아이템 가로 배치
            col_item, col_del = st.columns([5, 1])
            with col_item:
                btn_type = "primary" if is_selected else "secondary"
                # 말줄임 표시 처리
                title_display = f"{icon}  {item['title']}"
                if len(title_display) > 17:
                    title_display = title_display[:16] + "..."
                if st.button(title_display, key=f"sel_{item['id']}", use_container_width=True, type=btn_type):
                    storage["current_lesson_id"] = item["id"]
                    save_storage(storage)
                    st.rerun()
            with col_del:
                if st.button("×", key=f"del_{item['id']}", help="세션 삭제"):
                    del storage["lessons"][item["id"]]
                    if storage.get("current_lesson_id") == item["id"]:
                        rem = list(storage["lessons"].keys())
                        storage["current_lesson_id"] = rem[0] if rem else None
                    save_storage(storage)
                    st.rerun()

    # 5) 하단 고정 설정 (Bottom Settings Drawer)
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    with st.expander("⚙️  설정 및 API 키"):
        api_key_input = st.text_input(
            "Gemini API Key",
            value=storage.get("api_key", ""),
            type="password",
            placeholder="AI Studio 키 입력"
        )
        if api_key_input != storage.get("api_key", ""):
            storage["api_key"] = api_key_input
            save_storage(storage)
            st.success("API 키 저장 완료")
            st.rerun()

        slow_tts = st.toggle("🐢 느린 발음 모드", value=False)
        
        if storage.get("lessons"):
            if st.button("🧹 전체 대화 삭제", use_container_width=True):
                storage["lessons"] = {}
                storage["current_lesson_id"] = None
                save_storage(storage)
                st.rerun()
# ==========================================
# 5. 메인 화면 [1]: 📑 맞춤 학습 센터 (모바일 가로 스와이프 점프 칩)
# ==========================================
if app_mode == "📑 맞춤 학습 센터":
    current_id = storage.get("current_lesson_id")
    current_lesson = storage["lessons"].get(current_id) if current_id else None

    if not current_lesson:
        st.info("👈 왼쪽 사이드바에서 **[➕ 새 맞춤 학습 만들기]**를 선택해 주세요.")
    else:
        st.header(f"📖 {current_lesson['title']}")
        st.caption(f"{current_lesson['created_at']} | {current_lesson['mode']}")

        # 모바일 앱 스타일 가로 스와이프 칩 바
        st.markdown("""
        <div class="toc-scroll-wrapper">
            <a class="toc-chip" href="#sec-expr">📌 핵심 표현</a>
            <a class="toc-chip" href="#sec-read">📧 실전 독해</a>
            <a class="toc-chip" href="#sec-vocab">📝 핵심 단어장</a>
            <a class="toc-chip" href="#sec-quiz">☑️ 복습 퀴즈</a>
            <a class="toc-chip" href="#sec-tts-vocab">🔊 발음 듣기 & 단어 추가</a>
        </div>
        """, unsafe_allow_html=True)

        anchored_md = inject_section_anchors(current_lesson["content"])
        styled_content = enlarge_sinhala_only(anchored_md)
        st.markdown(styled_content, unsafe_allow_html=True)
        st.divider()

        # 주요 문장 발음 듣기 섹션
        st.markdown('<div id="sec-tts-vocab"></div>', unsafe_allow_html=True)
        st.subheader("🔊 본문 주요 문장 발음 듣기 & 저장")
        sentence_blocks = extract_sentence_blocks(current_lesson["content"])
        if sentence_blocks:
            for idx, blk in enumerate(sentence_blocks, 1):
                with st.container(border=True):
                    st.markdown(f"<div class='ko-meaning'>{idx}. 뜻: {blk.get('meaning', '뜻 미기재')}</div>", unsafe_allow_html=True)
                    st.markdown(enlarge_sinhala_only(blk.get("sinhala", "")), unsafe_allow_html=True)
                    st.markdown(f"🗣️ **한글 발음:** **{blk.get('pronun', '발음 미기재')}**")
                    
                    c_audio, c_btn = st.columns([3, 1])
                    with c_audio:
                        audio_path = get_audio_file(blk.get("sinhala", ""), slow=slow_tts)
                        if audio_path and os.path.exists(audio_path):
                            st.audio(audio_path, format="audio/mp3")
                    with c_btn:
                        if st.button("➕ 저장", key=f"save_sent_{current_id}_{idx}", use_container_width=True):
                            add_to_vocab(storage, {
                                "lesson_title": current_lesson["title"],
                                "type": "문장/표현",
                                "sinhala": blk.get("sinhala", ""),
                                "pronun": blk.get("pronun", ""),
                                "meaning": blk.get("meaning", ""),
                                "note": blk.get("mapping", "")
                            })
                            st.toast("✅ 단어장에 저장되었습니다!")

        extracted_words = extract_vocab_table(current_lesson["content"])
        if extracted_words:
            st.divider()
            col_title, col_all_btn = st.columns([3, 2])
            with col_title:
                st.subheader(f"📝 핵심 단어장 ({len(extracted_words)}개)")
            with col_all_btn:
                if st.button(f"📥 단어 {len(extracted_words)}개 일괄 추가", type="primary", use_container_width=True):
                    cnt = 0
                    for w in extracted_words:
                        r = add_to_vocab(storage, {
                            "lesson_title": current_lesson["title"],
                            "type": "단어",
                            "sinhala": w["sinhala"],
                            "pronun": w["pronun"],
                            "meaning": w["meaning"],
                            "note": w["note"]
                        })
                        if r in ["added", "updated"]:
                            cnt += 1
                    st.toast(f"✅ {cnt}개 단어가 추가되었습니다!")

            for w_idx, w in enumerate(extracted_words, 1):
                with st.container(border=True):
                    st.markdown(f"<div class='ko-meaning'>{w_idx}. 뜻: {w['meaning']}</div>", unsafe_allow_html=True)
                    st.markdown(enlarge_sinhala_only(w["sinhala"]), unsafe_allow_html=True)
                    st.markdown(f"🗣️ **발음:** **{w['pronun']}**")
                    if w.get("note"):
                        st.caption(f"💡 {w['note']}")
                    
                    wc_audio, wc_btn = st.columns([3, 1])
                    with wc_audio:
                        w_audio = get_audio_file(w["sinhala"], slow=slow_tts)
                        if w_audio and os.path.exists(w_audio):
                            st.audio(w_audio, format="audio/mp3")
                    with wc_btn:
                        if st.button("➕ 추가", key=f"save_word_{current_id}_{w_idx}", use_container_width=True):
                            add_to_vocab(storage, {
                                "lesson_title": current_lesson["title"],
                                "type": "단어",
                                "sinhala": w["sinhala"],
                                "pronun": w["pronun"],
                                "meaning": w["meaning"],
                                "note": w["note"]
                            })
                            st.toast(f"✅ '{w['meaning']}' 저장 완료!")

# ==========================================
# 6. 메인 화면 [2]: 🎙️ 실시간 AI 튜터
# ==========================================
elif app_mode == "🎙️ 실시간 AI 튜터 (음성 대화방)":
    current_id = storage.get("current_lesson_id")
    current_lesson = storage["lessons"].get(current_id) if current_id else None

    if current_lesson:
        st.header(f"🎙️ AI 튜터 — {current_lesson['title']}")
    else:
        st.header("🎙️ 새 음성 대화")
        st.info("화면 우측 하단의 **빨간색 원형 마이크 버튼**을 터치하여 녹음해 보세요!")

    mic_key = f"floating_mic_{current_id if current_id else 'new'}"
    audio_input = st.audio_input("우측 하단 원형 버튼 터치로 녹음 시작/종료", key=mic_key)
    
    if audio_input is not None or st.session_state.get("last_audio"):
        st.markdown("##### 🎧 내 녹음 음성 다시 듣기")
        st.audio(audio_input.getvalue() if audio_input else st.session_state.last_audio, format="audio/wav")

    text_input = st.chat_input("한글 발음이나 질문을 입력하세요...")
    st.divider()

    chat_box = st.container()
    if current_lesson:
        with chat_box:
            for c_idx, msg in enumerate(current_lesson.get("chat_history", [])):
                with st.chat_message(msg["role"]):
                    st.markdown(enlarge_sinhala_only(msg["content"]), unsafe_allow_html=True)
                    if msg["role"] == "assistant":
                        si_chunks = re.findall(r'[\u0D80-\u0DFF]+(?:\s+[\u0D80-\u0DFF]+)*', msg["content"])
                        unique_si = []
                        for sc in si_chunks:
                            if len(sc.strip()) > 1 and sc.strip() not in unique_si:
                                unique_si.append(sc.strip())
                        if unique_si:
                            st.caption("🔊 **AI 교정 발음 듣기:**")
                            for u_idx, u_si in enumerate(unique_si):
                                ac1, ac2 = st.columns([3, 2])
                                with ac1:
                                    st.markdown(enlarge_sinhala_only(u_si), unsafe_allow_html=True)
                                with ac2:
                                    u_audio = get_audio_file(u_si, slow=slow_tts)
                                    if u_audio and os.path.exists(u_audio):
                                        st.audio(u_audio, format="audio/mp3")

    if "last_audio" not in st.session_state:
        st.session_state.last_audio = None

    is_new_audio = False
    if audio_input is not None:
        audio_bytes = audio_input.getvalue()
        if audio_bytes != st.session_state.last_audio:
            st.session_state.last_audio = audio_bytes
            is_new_audio = True

    if text_input or is_new_audio:
        if not storage.get("api_key"):
            st.error("사이드바에서 Gemini API Key를 먼저 입력해 주세요.")
        else:
            client = genai.Client(api_key=storage["api_key"])
            lesson_ctx = current_lesson["content"] if current_lesson else "자유 음성 회화 및 발음 교정"
            recent_hist = "\n".join([
                f"{m['role']}: {m['content']}" 
                for m in (current_lesson.get("chat_history", [])[-6:] if current_lesson else [])
            ])

            try:
                if is_new_audio:
                    user_msg = "🎤 *[음성 녹음 전송됨]*"
                    with st.spinner("발음 및 어순 교정 분석 중..."):
                        prompt = get_tutor_prompt(
                            lesson_context=lesson_ctx,
                            chat_history=recent_hist,
                            user_input="첨부된 음성 녹음을 듣고 발음 정확도와 어순 교정, 모범 싱할라어 문장을 작성해 주세요. 첫 줄에 반드시 [주제: 10자 이내 요약 제목]을 적어주세요.",
                            is_audio=True
                        )
                        resp = client.models.generate_content(
                            model=MODEL_ID,
                            contents=[
                                prompt,
                                types.Part.from_bytes(
                                    data=st.session_state.last_audio,
                                    mime_type="audio/wav"
                                )
                            ]
                        )
                        reply = resp.text
                else:
                    user_msg = text_input
                    with st.spinner("답변 생성 중..."):
                        prompt = get_tutor_prompt(
                            lesson_context=lesson_ctx,
                            chat_history=recent_hist,
                            user_input=text_input,
                            is_audio=False
                        )
                        resp = client.models.generate_content(
                            model=MODEL_ID,
                            contents=prompt
                        )
                        reply = resp.text

                if not current_lesson:
                    m_title = re.search(r"\[주제:\s*([^\]]+)\]", reply)
                    if m_title:
                        auto_title = m_title.group(1).strip()
                    elif text_input:
                        auto_title = text_input[:14]
                    else:
                        auto_title = f"음성 대화 ({datetime.now().strftime('%m/%d %H:%M')})"

                    new_id = str(uuid.uuid4())[:8]
                    storage["lessons"][new_id] = {
                        "id": new_id,
                        "title": auto_title,
                        "mode": "음성 대화",
                        "level": "실시간 튜터링",
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "content": f"## 📌 핵심 표현 및 음성 학습 노트\n\n{reply}",
                        "chat_history": [
                            {"role": "user", "content": user_msg},
                            {"role": "assistant", "content": reply}
                        ]
                    }
                    storage["current_lesson_id"] = new_id
                else:
                    current_lesson["chat_history"].append({"role": "user", "content": user_msg})
                    current_lesson["chat_history"].append({"role": "assistant", "content": reply})

                save_storage(storage)
                st.rerun()

            except Exception as e:
                st.error(f"오류: {e}")

# ==========================================
# 7. 메인 화면 [3]: 📒 통합 단어장 & 퀴즈
# ==========================================
elif app_mode == "📒 통합 단어장 & 퀴즈":
    st.header("📒 통합 단어장 & 퀴즈")
    vocab_list = storage.get("vocab_notes", [])

    incomplete_items = [
        v for v in vocab_list
        if is_bad_meaning(v.get("meaning", "")) or is_bad_pronun(v.get("pronun", ""))
    ]
    if incomplete_items:
        st.warning(f"⚠️ 뜻/발음이 비어있는 단어: **{len(incomplete_items)}개**")
        if st.button("🪄 뜻/발음 AI 자동 완성", type="primary"):
            if not storage.get("api_key"):
                st.error("사이드바에서 API 키를 먼저 입력해 주세요.")
            else:
                with st.spinner("AI가 누락된 뜻과 한글 독음을 채우는 중..."):
                    try:
                        client = genai.Client(api_key=storage["api_key"])
                        query_lines = [f"{idx}|{it.get('sinhala', '')}" for idx, it in enumerate(incomplete_items)]
                        fix_prompt = (
                            "다음 싱할라어 문장/단어들의 한국어 뜻과 한국어 발음(한글 독음 + 로마자)을 작성해 주세요.\n"
                            "각 줄마다 `인덱스|한국어 뜻|[한글 발음] (로마자)` 형식으로 출력하세요.\n\n"
                            + "\n".join(query_lines)
                        )
                        res = client.models.generate_content(model=MODEL_ID, contents=fix_prompt)
                        for line in res.text.splitlines():
                            parts = [p.strip() for p in line.split("|")]
                            if len(parts) >= 3 and parts[0].isdigit():
                                idx = int(parts[0])
                                if 0 <= idx < len(incomplete_items):
                                    incomplete_items[idx]["meaning"] = parts[1]
                                    incomplete_items[idx]["pronun"] = parts[2]
                        save_storage(storage)
                        st.success("완료되었습니다!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")

    vocab_sub_mode = st.radio(
        "모드 선택",
        ["📋 목록", "🎴 플래시카드", "🎯 4지선다 퀴즈"],
        horizontal=True,
        key="vocab_sub_nav"
    )
    st.divider()

    # 1) 목록 모드
    if vocab_sub_mode == "📋 목록":
        with st.expander("➕ 단어 수동 등록"):
            c1, c2 = st.columns(2)
            with c1:
                v_type = st.selectbox("분류", ["단어", "문장/표현", "오답/교정"])
                v_sinhala = st.text_input("싱할라어 문자 (예: ස්තූතියි)")
                v_pronun = st.text_input("한글 독음 발음 (예: [스투티이])")
            with c2:
                v_meaning = st.text_input("한국어 뜻 (예: 감사합니다)")
                v_note = st.text_area("메모 / 어순 팁")
            if st.button("💾 저장", type="primary", use_container_width=True):
                if not v_meaning.strip() and not v_sinhala.strip():
                    st.warning("한국어 뜻이나 싱할라 문자를 입력하세요.")
                else:
                    add_to_vocab(storage, {
                        "lesson_title": "수동 등록",
                        "type": v_type,
                        "sinhala": v_sinhala.strip(),
                        "pronun": v_pronun.strip(),
                        "meaning": v_meaning.strip(),
                        "note": v_note.strip()
                    })
                    st.toast("✅ 저장되었습니다!")
                    st.rerun()

        if not vocab_list:
            st.info("등록된 단어가 없습니다.")
        else:
            filter_cat = st.radio("분류 필터", ["전체", "단어", "문장/표현", "오답/교정"], horizontal=True)
            filter_stat = st.radio("상태 필터", ["전체 보기", "🔥 미암기만", "⭐ 별표만", "✅ 완료만"], horizontal=True)

            filtered = []
            for item in vocab_list:
                if filter_cat != "전체" and item.get("type") != filter_cat:
                    continue
                if filter_stat == "🔥 미암기만" and item.get("mastered"):
                    continue
                if filter_stat == "⭐ 별표만" and not item.get("starred"):
                    continue
                if filter_stat == "✅ 완료만" and not item.get("mastered"):
                    continue
                filtered.append(item)

            for item in reversed(filtered):
                with st.container(border=True):
                    badge = "⭐ " if item.get("starred") else ""
                    done_badge = "✅ [완료] " if item.get("mastered") else ""
                    st.markdown(
                        f"<div class='ko-meaning'>{badge}{done_badge}[{item.get('type', '단어')}] 뜻: {item.get('meaning', '')}</div>",
                        unsafe_allow_html=True
                    )
                    if item.get("sinhala"):
                        st.markdown(enlarge_sinhala_only(item["sinhala"]), unsafe_allow_html=True)
                    st.markdown(f"🗣️ **발음:** **{item.get('pronun', '')}**")
                    if item.get("note"):
                        st.caption(f"💡 {item['note']}")

                    c_tts, b1, b2, b3 = st.columns([3, 1, 1, 1])
                    with c_tts:
                        sound_target = item.get("sinhala") or item.get("pronun")
                        v_audio = get_audio_file(sound_target, slow=slow_tts)
                        if v_audio and os.path.exists(v_audio):
                            st.audio(v_audio, format="audio/mp3")
                    with b1:
                        star_label = "⭐" if item.get("starred") else "☆"
                        if st.button(star_label, key=f"star_{item['id']}", use_container_width=True):
                            item["starred"] = not item.get("starred", False)
                            save_storage(storage)
                            st.rerun()
                    with b2:
                        mast_label = "✅" if item.get("mastered") else "⬜"
                        if st.button(mast_label, key=f"mast_{item['id']}", use_container_width=True):
                            item["mastered"] = not item.get("mastered", False)
                            save_storage(storage)
                            st.rerun()
                    with b3:
                        if st.button("🗑️", key=f"del_v_{item['id']}", use_container_width=True):
                            storage["vocab_notes"] = [x for x in storage["vocab_notes"] if x["id"] != item["id"]]
                            save_storage(storage)
                            st.toast("삭제되었습니다.")
                            st.rerun()

    # 2) 플래시카드 모드
    elif vocab_sub_mode == "🎴 플래시카드":
        if not vocab_list:
            st.info("단어장에 단어를 먼저 등록해 주세요.")
        else:
            fc_opt1, fc_opt2 = st.columns(2)
            with fc_opt1:
                only_unmastered = st.checkbox("🔥 미암기 카드만 보기", value=False)
            with fc_opt2:
                card_direction = st.radio("앞면", ["싱할라 문자 먼저", "한국어 뜻 먼저"], horizontal=True)

            deck = [x for x in vocab_list if not x.get("mastered")] if only_unmastered else vocab_list

            if not deck:
                st.success("🎉 모든 카드를 암기했습니다!")
            else:
                if "fc_idx" not in st.session_state:
                    st.session_state.fc_idx = 0
                if "fc_flipped" not in st.session_state:
                    st.session_state.fc_flipped = False

                idx = st.session_state.fc_idx % len(deck)
                card = deck[idx]

                st.progress((idx + 1) / len(deck), text=f"진행도: {idx + 1} / {len(deck)}")

                if card_direction.startswith("싱할라"):
                    front_html = f"""
                    <div class="flashcard">
                        <div class="flashcard-sub">[{card.get('type', '단어')}] 다음 표현의 뜻은?</div>
                        <div class="si-char-xl">{card.get('sinhala') or '문자 없음'}</div>
                        <div class="ko-pronun">🗣️ {card.get('pronun', '')}</div>
                    </div>
                    """
                else:
                    front_html = f"""
                    <div class="flashcard">
                        <div class="flashcard-sub">[{card.get('type', '단어')}] 다음 뜻을 싱할라어로?</div>
                        <div class="ko-meaning-xl">뜻: {card.get('meaning', '')}</div>
                    </div>
                    """

                st.markdown(front_html, unsafe_allow_html=True)

                fc_audio = get_audio_file(card.get("sinhala") or card.get("pronun"), slow=slow_tts)
                if fc_audio and os.path.exists(fc_audio):
                    st.audio(fc_audio, format="audio/mp3")

                # 모바일 터치 최적화 2x2 버튼 그리드
                g1, g2 = st.columns(2)
                with g1:
                    if st.button("🔄 뜻 뒤집기", type="primary", use_container_width=True):
                        st.session_state.fc_flipped = not st.session_state.fc_flipped
                        st.rerun()
                with g2:
                    if st.button("✅ 암기 완료", use_container_width=True):
                        card["mastered"] = True
                        save_storage(storage)
                        st.session_state.fc_flipped = False
                        st.toast("🎉 완료 처리되었습니다!")
                        st.rerun()

                g3, g4 = st.columns(2)
                with g3:
                    if st.button("⬅️ 이전 카드", use_container_width=True):
                        next_i = (idx - 1) % len(deck)
                        st.session_state.fc_idx = next_i
                        st.session_state.fc_flipped = False
                        next_card = deck[next_i]
                        st.session_state.autoplay_file = get_audio_file(next_card.get("sinhala") or next_card.get("pronun"), slow=slow_tts)
                        st.rerun()
                with g4:
                    if st.button("➡️ 다음 카드", use_container_width=True):
                        next_i = (idx + 1) % len(deck)
                        st.session_state.fc_idx = next_i
                        st.session_state.fc_flipped = False
                        next_card = deck[next_i]
                        st.session_state.autoplay_file = get_audio_file(next_card.get("sinhala") or next_card.get("pronun"), slow=slow_tts)
                        st.rerun()

                if st.session_state.fc_flipped:
                    st.success(f"### 🎯 뜻: {card.get('meaning', '')}")
                    st.markdown(f"**싱할라 문자:** {enlarge_sinhala_only(card.get('sinhala', ''))}", unsafe_allow_html=True)
                    st.markdown(f"**🗣️ 독음:** **{card.get('pronun', '')}**")
                    if card.get("note"):
                        st.info(f"💡 {card['note']}")

    # 3) 4지선다 퀴즈 모드
    elif vocab_sub_mode == "🎯 4지선다 퀴즈":
        st.subheader("🎯 실전 4지선다 퀴즈")
        if len(vocab_list) < 4:
            st.warning(f"단어가 4개 이상 필요합니다. (현재: {len(vocab_list)}개)")
        else:
            if "quiz_q" not in st.session_state or st.session_state.quiz_q is None:
                target = random.choice(vocab_list)
                others = [x for x in vocab_list if x["id"] != target["id"]]
                wrongs = random.sample(others, min(3, len(others)))
                options = [target] + wrongs
                random.shuffle(options)
                st.session_state.quiz_q = target
                st.session_state.quiz_opts = options
                st.session_state.quiz_msg = None
                st.session_state.show_balloons_once = False

            if st.session_state.get("show_balloons_once"):
                st.balloons()
                st.session_state.show_balloons_once = False

            q_card = st.session_state.quiz_q
            st.markdown(f"""
            <div class="flashcard">
                <div class="flashcard-sub">다음 싱할라어의 알맞은 한국어 뜻은?</div>
                <div class="si-char-xl">{q_card.get('sinhala', '')}</div>
                <div class="ko-pronun">🗣️ {q_card.get('pronun', '')}</div>
            </div>
            """, unsafe_allow_html=True)

            q_audio = get_audio_file(q_card.get("sinhala") or q_card.get("pronun"), slow=slow_tts)
            if q_audio and os.path.exists(q_audio):
                st.audio(q_audio, format="audio/mp3")

            for i, opt in enumerate(st.session_state.quiz_opts, 1):
                btn_label = f"{i}. {opt.get('meaning', '뜻 미기재')}"
                if st.button(btn_label, key=f"q_opt_{i}", use_container_width=True):
                    if opt["id"] == q_card["id"]:
                        st.session_state.quiz_msg = ("success", f"⭕ 정답입니다! — 뜻: **{q_card.get('meaning')}**")
                        st.session_state.show_balloons_once = True
                        st.session_state.autoplay_file = q_audio
                        st.rerun()
                    else:
                        st.session_state.quiz_msg = ("error", f"❌ 오답입니다! 선택한 '{opt.get('meaning')}'의 발음은 {opt.get('pronun')} 입니다.")
                        st.session_state.show_balloons_once = False
                        st.rerun()

            if st.session_state.get("quiz_msg"):
                m_type, m_text = st.session_state.quiz_msg
                if m_type == "success":
                    st.success(m_text)
                else:
                    st.error(m_text)

            if st.button("➡️ 다음 문제 (자동 발음)", type="primary", use_container_width=True):
                target = random.choice(vocab_list)
                others = [x for x in vocab_list if x["id"] != target["id"]]
                wrongs = random.sample(others, min(3, len(others)))
                options = [target] + wrongs
                random.shuffle(options)
                st.session_state.quiz_q = target
                st.session_state.quiz_opts = options
                st.session_state.quiz_msg = None
                st.session_state.show_balloons_once = False
                st.session_state.autoplay_file = get_audio_file(target.get("sinhala") or target.get("pronun"), slow=slow_tts)
                st.rerun()