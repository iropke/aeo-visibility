"""v1 (MVP) scoring 모듈 — 참고용 보존 (SPEC §7-3).

dict 기반 score() 시그니처. v2는 ``app.scoring`` 의 표준 ``CategoryMetrics``
스키마 + ``analyze(url, options)`` 시그니처 사용.

이 패키지는 ``app.services.crawler.CrawlData`` 와 ``app.services.analyzer``
(이미 dead code) 만 의존. v1 라우터(``analysis.py``)는 main.py에 미등록 상태이며
런타임 호출 시 dropped table(``analysis_results`` v1 스키마) 때문에 실패함.

향후 정리 시점은 사용자 결정.
"""
