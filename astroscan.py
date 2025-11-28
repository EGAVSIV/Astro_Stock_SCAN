# ---------------------------------------------------------------------
# TAB 2 — STOCKS SCAN
# ---------------------------------------------------------------------
with tabs[1]:
    st.subheader("Scan Stocks Around Aspect Start Dates")

    aspect_dates = st.session_state["aspect_dates_past"]
    if not aspect_dates:
        st.warning("No aspect dates available. Go to the Aspects tab and compute first.")
    else:
        st.caption(f"Using {len(aspect_dates)} past aspect start dates.")

        if st.button("🚀 Run Stock Scan"):
            files = requests.get(GITHUB_DIR_API).json()
            results = []
            total_files = len([f for f in files if f["name"].endswith(".parquet")])

            with st.spinner("Scanning stocks from GitHub parquet files..."):
                for f in files:
                    name = f.get("name", "")
                    if not name.endswith(".parquet"):
                        continue

                    sym = name.replace(".parquet", "")
                    url = f["download_url"]

                    try:
                        df = load_github_df(url)
                    except Exception:
                        continue

                    items = analyze_symbol_for_aspect_dates(df, aspect_dates)

                    for it in items:
                        if (it["pct_max"] >= 10.0) or (it["pct_min"] <= -10.0):
                            aspect_type = f"{planet1} {aspect_name} {planet2}"
                            move_category = "😆 >10% Gain" if it["pct_max"] >= 10 else "😩 >10% Fall"

                            results.append(
                                {
                                    "symbol": sym,
                                    "aspect_date": it["aspect_date"],
                                    "close": it["close"],
                                    "max10": it["max10"],
                                    "min10": it["min10"],
                                    "pct_max": round(it["pct_max"], 2),
                                    "pct_min": round(it["pct_min"], 2),
                                    "Aspect": aspect_type,
                                    "Move Category": move_category,
                                }
                            )

            df_res = pd.DataFrame(results)

            # ⭐ ADD STOCK COUNT COLUMN
            if not df_res.empty:
                df_res["Count"] = df_res.groupby("symbol")["symbol"].transform("count")

            st.session_state["scan_results"] = df_res
            st.success(f"Scan complete. {len(df_res)} qualifying records found.")

        st.markdown("### Scan Results")

        df_res = st.session_state["scan_results"]

        if df_res.empty:
            st.info("No results yet. Run a scan to populate data.")
        else:

            # ⭐ MULTIPLE HIT FILTER
            min_hits = st.slider("Show stocks repeating at least N times", 1, 10, 1)
            df_filtered = df_res[df_res["Count"] >= min_hits]

            st.dataframe(df_filtered, use_container_width=True)

            # ⭐ CSV DOWNLOAD button
            csv = df_filtered.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Download Filtered CSV",
                csv,
                f"aspect_scan_filtered.csv",
                "text/csv"
            )

            # Small summary
            st.success(f"Stocks meeting criteria: {df_filtered['symbol'].nunique()}")
