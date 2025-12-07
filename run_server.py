#!/usr/bin/env python
"""
Quote Origin API 서버 실행 스크립트

사용법:
  python run_server.py              # 기본 포트 8000
  python run_server.py --port 9000  # 포트 9000
  python run_server.py --host 127.0.0.1 --port 8080  # 127.0.0.1:8080
"""

import argparse
import logging
import sys
import os

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Quote Origin API 서버 실행"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="서버 호스트 (기본값: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="서버 포트 (기본값: 8000)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="코드 변경 시 자동 재시작 (개발 모드)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="워커 프로세스 수 (기본값: 1)"
    )
    
    args = parser.parse_args()
    
    # 환경변수 설정
    os.environ["API_HOST"] = args.host
    os.environ["API_PORT"] = str(args.port)
    
    logger.info("=" * 80)
    logger.info("Quote Origin API 서버 시작")
    logger.info("=" * 80)
    logger.info(f"Host: {args.host}")
    logger.info(f"Port: {args.port}")
    logger.info(f"Reload: {args.reload}")
    logger.info(f"Workers: {args.workers}")
    logger.info("=" * 80)
    logger.info("API 문서: http://{}:{}/docs".format(args.host, args.port))
    logger.info("API 문서 (ReDoc): http://{}:{}/redoc".format(args.host, args.port))
    logger.info("=" * 80)
    
    try:
        import uvicorn
        from qdd2.backend_api import app
        
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            reload=args.reload,
            workers=args.workers,
            log_level="info"
        )
    
    except ImportError as e:
        logger.error(f"필수 패키지 누락: {e}")
        logger.error("다음 명령어로 설치하세요:")
        logger.error("  pip install fastapi uvicorn pydantic")
        sys.exit(1)
    except Exception as e:
        logger.error(f"서버 실행 오류: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
