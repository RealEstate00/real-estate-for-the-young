# run.py

import argparse
from .pipeline import run_localdata_pipeline, run_seoul_pipeline


def main():
    parser = argparse.ArgumentParser(description="🔎 공공데이터 수집 실행")
    parser.add_argument(
        "--source", choices=["localdata", "seoul"], required=True,
        help="데이터 출처 선택: 'localdata' 또는 'seoul'"
    )
    parser.add_argument(
        "--service", default="SearchSTNBySubwayLineInfo",
        help="서울 열린데이터광장 API의 서비스명 지정 (예: TbPharmacyOperateInfo, ChildCareInfo 등). 'all' 입력 시 전체 실행"
    )
    parser.add_argument("--csv", action="store_true", help="CSV 저장 여부")
    parser.add_argument("--db", action="store_true", help="DB 저장 여부")

    parser.add_argument("--start_date", help="변동 데이터 조회 시작일자 (YYYYMMDD)")
    parser.add_argument("--end_date", help="변동 데이터 조회 종료일자 (YYYYMMDD)")

    args = parser.parse_args()

    if args.source == "localdata":
        print("[INFO] 로컬데이터 포털 수집 시작...")
        run_localdata_pipeline(
            save_csv=args.csv,
            save_db=args.db,
            start_date=args.start_date,
            end_date=args.end_date
        )

    elif args.source == "seoul":
        if args.service == "all":
            all_services = [
                "SearchSTNBySubwayLineInfo",  # 주소없는 지하철역(호선정보 있음)
                "TbPharmacyOperateInfo",
                "ChildCareInfo",
                "childSchoolInfo",
                "neisSchoolInfo",
                "SebcCollegeInfoKor",
                "SearchParkInfoService",
                "vBigJtrFlrCbOuln",
                "busStopLocationXyInfo"
                "StationAdresTelno"   # 주소있는 지하철역(호선정보 불완전)
            ]
            for service in all_services:
                print(f"[INFO] 서울 API 수집 - {service} 시작...")
                run_seoul_pipeline(service_name=service, save_csv=args.csv, save_db=args.db)
        else:
            print(f"[INFO] 서울 API 수집 - {args.service} 시작...")
            run_seoul_pipeline(service_name=args.service, save_csv=args.csv, save_db=args.db)


if __name__ == "__main__":
    main()
