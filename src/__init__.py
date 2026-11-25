"""여러 노트북에서 같이 쓰는 함수 모음.

노트북 첫 셀:
    %load_ext autoreload
    %autoreload 2
    import sys; sys.path.append("..")
    from src import config, loaders, calendar_kr, routes, metrics, geo, viz
    viz.setup_plot()

모듈
- config:      폴더 경로, 팀이 정하기 전 임시값(출퇴근 시간대·역 반경 등), 출처 문구
- loaders:     data/raw/ 원본 읽기(인코딩·컬럼명·값 표기 통일), 대여이력 zip → 월별 parquet
- calendar_kr: 공휴일 표, 평일/주말·공휴일 구분, 출근/퇴근 시간대 구분, 기간 날 수
- routes:      노선(대여소→반납소) × 시간대별 평일 출현일수, 반복 노선·역방향 반복 표시 (분석 ②)
- geo:         거리 계산, 가장 가까운 지하철역, 역 인근 구분
- metrics:     하루 평균 시간대별 이용, 주말 기준선 통근 비중, 대여소 통근 지수 (② 교차 확인)
- viz:         한글 폰트, 그래프·표 출처 표기, 그림 저장
"""
