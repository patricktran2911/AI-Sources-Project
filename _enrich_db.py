"""
Enrich the knowledge database with additional global chunks.

Run once after initial seed to add more comprehensive Q&A-optimised knowledge:
  py -3.12 _enrich_db.py

Inserts with ON CONFLICT DO NOTHING — safe to run multiple times.
All chunks are global (user_id=NULL) in the appropriate context.
"""

import asyncio
import json
import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

# ── Extra knowledge chunks ────────────────────────────────────────────────────
# Format: (id, context, category, text)
CHUNKS = [
    # ── profile — hiring / availability ────────────────────────────────────
    (
        "profile_hiring_cta",
        "profile",
        "Hiring Info",
        "Patrick Tran is actively seeking full-time software engineering roles as of 2026. "
        "He is immediately available — he is not waiting to graduate. "
        "The best way to reach him is by email at patricktran291197@gmail.com or via "
        "LinkedIn at https://www.linkedin.com/in/patrick-tran-99768828a/. "
        "He is open to iOS engineer, full-stack, backend, AI/ML, and any software "
        "engineering roles across all industries (except chemical), in remote, hybrid, or "
        "on-site settings.",
    ),
    (
        "profile_experience_timeline",
        "profile",
        "Work History",
        "Patrick Tran's professional experience timeline: "
        "Scoop Inc. iOS Intern (May–Sep 2023) — carpooling app, SwiftUI/UIKit; "
        "FanFly iOS Engineer (Oct 2023–Dec 2024) — fan-artist ticket platform, led first iOS app; "
        "NeuroSpring Full-Stack Engineer (Feb–Dec 2025) — hospital movement-detection platform, "
        "React + FastAPI + Supabase + AI; "
        "Mocanik LLC Full-Stack Developer (Jan 2026–present) — web apps with JavaScript and PHP. "
        "Total: 4+ years of professional software engineering experience.",
    ),
    (
        "profile_strongest_skills",
        "profile",
        "Core Strengths",
        "Patrick Tran's three strongest technical areas are: "
        "(1) iOS development — shipped apps to the App Store using Swift and SwiftUI; "
        "(2) Python backend — built production FastAPI services with asyncpg, PostgreSQL, and Docker; "
        "(3) AI/ML integration — trained PyTorch models, integrated MediaPipe and LLMs in "
        "production systems. He is a T-shaped engineer: deep in iOS and Python, broad across "
        "the full stack.",
    ),
    (
        "profile_education_summary",
        "profile",
        "Education",
        "Patrick Tran holds a Bachelor of Science in Computer Science from California State "
        "University, Sacramento (Sacramento State), graduating May 22, 2026 with a GPA of 3.2. "
        "Before transferring, he attended Cosumnes River College starting in 2020. "
        "Earlier schooling: Hoàng Văn Thụ Primary School, Huỳnh Thúc Kháng Middle School, "
        "Hồng Hà High School, and one year at Ho Chi Minh City University of Technology "
        "before moving to the United States.",
    ),
    (
        "profile_app_store_apps",
        "profile",
        "Published Apps",
        "Patrick has shipped two iOS apps to the Apple App Store: "
        "(1) FanFly — currently live; a fan-artist show ticket platform he led as iOS engineer; "
        "(2) iUSC Naturalization Study App — currently unlisted (developer account not renewed); "
        "an adaptive flashcard and quiz app for the U.S. naturalization test he built independently.",
    ),
    (
        "profile_why_hire",
        "profile",
        "Value Proposition",
        "Reasons to hire Patrick Tran: broad full-stack skills spanning mobile, web, backend, and "
        "AI/ML; track record of shipping real products to production; fast learner who picks up "
        "new technologies quickly; strong debugger and optimizer; uses AI tools effectively to "
        "accelerate development; solid understanding of clean architecture and design patterns; "
        "4+ years of professional experience; graduating with a CS degree May 2026.",
    ),
    (
        "profile_github_repos",
        "profile",
        "GitHub Repositories",
        "Patrick Tran's GitHub username is patricktran2911. Notable public repositories: "
        "STEMSight PIM (medical AI GCN model) at https://github.com/STEMSight-Project/PIM; "
        "AI Combination Server (RAG backend) at https://github.com/patricktran2911/AI-Sources-Project; "
        "Portfolio website at https://github.com/patricktran2911/patrick-website; "
        "iUSC Naturalization App at https://github.com/patricktran2911/iUSC.",
    ),
    (
        "profile_salary_location",
        "profile",
        "Job Preferences",
        "Patrick Tran is based in Sacramento, California (PST timezone). "
        "He is open to fully remote work, hybrid, or on-site in Sacramento or nearby areas. "
        "His preferred career path is: startup → mid-size company → big tech. "
        "He is available immediately and open to full-time, contract, or part-time roles.",
    ),

    # ── profile — technical depth ───────────────────────────────────────────
    (
        "profile_python_depth",
        "profile",
        "Python Skills",
        "Patrick Tran has deep experience with Python, specifically: FastAPI for async REST APIs, "
        "asyncpg for PostgreSQL connections, SQLAlchemy for ORM, PyTorch for model training, "
        "sentence-transformers for embeddings, boto3 for AWS integrations, Docker for "
        "containerisation, and general scripting. He has built production Python backends "
        "with PostgreSQL, AWS RDS, and S3.",
    ),
    (
        "profile_swift_depth",
        "profile",
        "Swift/iOS Skills",
        "Patrick Tran has 4+ years of Swift development experience: SwiftUI for declarative UI "
        "(modular component architecture, reusable templates), UIKit for legacy and complex "
        "custom views, PromiseKit and Alamofire for async networking, Firebase for authentication "
        "and analytics, and App Store submission and maintenance. He has shipped apps used by "
        "real users.",
    ),
    (
        "profile_ai_depth",
        "profile",
        "AI/ML Skills",
        "Patrick Tran's AI/ML experience: trained and deployed a Graph Convolutional Network "
        "(UNIK) achieving 82.88% accuracy on medical movement classification; built full ML "
        "pipelines (data extraction → preprocessing → training → inference API); integrated "
        "MediaPipe PoseLandmarker for real-time skeleton extraction; built RAG systems with "
        "semantic retrieval and cross-encoder reranking; works with OpenAI, Anthropic, and "
        "Gemini LLM APIs; experience with HuggingFace Transformers and sentence-transformers.",
    ),

    # ── projects — richer descriptions ─────────────────────────────────────
    (
        "project_ai_combo_detail",
        "projects",
        "AI Combination Server",
        "The AI Combination Server (this project) is Patrick's most recent backend project "
        "(2025–2026). It is a production-ready multi-feature AI backend with: "
        "pluggable LLM providers (OpenAI, Anthropic, Gemini); "
        "RAG pipeline using sentence-transformers for semantic retrieval and cross-encoder for "
        "reranking; PostgreSQL (AWS RDS) for knowledge storage with per-user scoping; "
        "SSE streaming for real-time chat; FastAPI with asyncpg; Docker for local dev; "
        "automated migrations and JSON seed on startup; "
        "knowledge management API for adding/listing/deleting custom knowledge per user. "
        "GitHub: https://github.com/patricktran2911/AI-Sources-Project.",
    ),
    (
        "project_pim_detail",
        "projects",
        "PIM Technical Detail",
        "The STEMSight PIM project classifies 10 Parkinson's movement types: "
        "ballistic, chorea, decerebrate, decorticate, dystonia, fencer_posture, "
        "myoclonus, normal, tremor, versive_head. "
        "Architecture: MediaPipe PoseLandmarker extracts 33 skeletal joints from video at 60 FPS; "
        "300 frames (5 seconds) per sample; reshaped to UNIK input format (N, 3, 300, 33, 1); "
        "UNIK Spatial-Temporal GCN classifies the movement. "
        "Training: 2080 samples train / 520 test; 82.88% accuracy (431/520 correct). "
        "Inference via FastAPI endpoint accepting video or live camera feed.",
    ),
    (
        "project_neurospring_detail",
        "projects",
        "NeuroSpring Technical Detail",
        "The NeuroSpring Hospital Monitoring Platform (Feb–Dec 2025) is a real-time system "
        "for hospital patient monitoring. Patrick built: "
        "React + TypeScript UI for web browsers and Raspberry Pi devices; "
        "FastAPI backend with Supabase (PostgreSQL) real-time data; "
        "MediaPipe integration for live camera movement analysis; "
        "UNIK AI model integration for posture classifications; "
        "deployed on web + embedded Raspberry Pi hardware in hospital rooms. "
        "The system triggers rapid ambulance deployment on detection.",
    ),

    # ── general — assistant purpose ─────────────────────────────────────────
    (
        "general_assistant_purpose",
        "general",
        "Assistant Purpose",
        "This AI assistant is Patrick Tran's personal AI representative. "
        "It can answer questions about: Patrick's skills and technical expertise; "
        "his work experience and employment history; his projects and GitHub repos; "
        "his portfolio and published apps; his education; how to contact or hire him; "
        "his availability and job preferences. "
        "Available contexts: 'profile' (personal/career info), 'projects' (technical work), "
        "'portfolio' (showcase), 'general' (this system). "
        "Use 'auto' for automatic context detection.",
    ),
    (
        "general_about_patrick",
        "general",
        "About Patrick",
        "Patrick Tran is a 27-year-old iOS and full-stack software engineer based in "
        "Sacramento, California. He was born in Vietnam and moved to the US at age 19. "
        "He is graduating with a BS in Computer Science from Sacramento State on May 22, 2026. "
        "He has 4+ years of professional experience and is immediately available for new roles. "
        "Contact: patricktran291197@gmail.com | "
        "LinkedIn: https://www.linkedin.com/in/patrick-tran-99768828a/ | "
        "Website: https://www.patrickcs-web.com/ | "
        "GitHub: https://github.com/patricktran2911",
    ),

    # ── projects — AI index chunk to improve context routing ───────────────
    (
        "projects_ai_overview",
        "projects",
        "AI Projects Overview",
        "Patrick Tran built multiple AI and machine learning projects: "
        "STEMSight PIM — medical AI using PyTorch GCN for Parkinsons movement classification (82.88% accuracy); "
        "AI Combination Server — production RAG backend with semantic retrieval and LLM integration; "
        "NeuroSpring — hospital AI monitoring platform with MediaPipe posture and movement classification; "
        "AI Posture Correction — real-time posture analysis app (in progress). "
        "All AI projects use Python, PyTorch or transformer models, deployed via FastAPI backends.",
    ),

    # ── portfolio — richer descriptions ────────────────────────────────────
    (
        "portfolio_summary",
        "portfolio",
        "Portfolio Overview",
        "Patrick Tran's portfolio of shipped and notable projects: "
        "FanFly iOS App (live on App Store) — led development; "
        "iUSC Naturalization App (App Store, unlisted) — built independently; "
        "NeuroSpring Hospital Platform (production) — real-time AI movement detection; "
        "STEMSight PIM (production) — medical AI, 82.88% accuracy; "
        "AI Combination Server (production) — RAG-powered AI backend; "
        "Personal Portfolio Website (live) — https://www.patrickcs-web.com/; "
        "Medical Ocean (academic) — hospital management system (Sacramento State). "
        "Spans mobile iOS, healthcare AI, web, and backend domains.",
    ),
]


async def main() -> None:
    from app.database.connection import create_pool
    from app.database.migrations import run_migrations
    from app.core.config import get_settings

    settings = get_settings()
    print(f"Target: {settings.database_url}")
    pool = await create_pool(settings.database_url)
    await run_migrations(pool)  # ensure table exists

    INSERT = """
    INSERT INTO knowledge_chunks (id, context, text, category, metadata, user_id)
    VALUES ($1, $2, $3, $4, $5, NULL)
    ON CONFLICT DO NOTHING;
    """

    inserted = 0
    skipped = 0
    async with pool.acquire() as conn:
        for chunk_id, context, category, text in CHUNKS:
            result = await conn.execute(INSERT, chunk_id, context, text, category, json.dumps({}))
            # result is like "INSERT 0 1" or "INSERT 0 0"
            if result.endswith("1"):
                inserted += 1
                print(f"  + [{context}] {chunk_id}")
            else:
                skipped += 1
                print(f"  ~ [{context}] {chunk_id}  (already exists)")

    await pool.close()

    print()
    print(f"Done — {inserted} inserted, {skipped} already existed.")

    # Print totals per context
    pool2 = await create_pool(settings.database_url)
    async with pool2.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT context, COUNT(*) AS cnt
            FROM knowledge_chunks WHERE user_id IS NULL
            GROUP BY context ORDER BY context
            """
        )
        print()
        print("=== Global chunks in DB ===")
        total = 0
        for r in rows:
            print(f"  {r['context']:<20}  {r['cnt']:>3} chunks")
            total += r["cnt"]
        print(f"  {'TOTAL':<20}  {total:>3} chunks")
    await pool2.close()


asyncio.run(main())
