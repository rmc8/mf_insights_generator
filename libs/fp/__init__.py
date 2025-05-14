import pandas as pd


class FinancialPlanner:
    AMOUNT_COLUMN = "金額（円）"
    AMOUNT_NUMERIC_COLUMN = "金額_数値"

    def __init__(self, df: pd.DataFrame):
        """
        FinancialPlanner クラスの初期化。

        Args:
            df (pd.DataFrame): MoneyForwardから読み込んだ生の家計簿データ。
        """
        self.df = df
        self._processed_df: pd.DataFrame | None = None

    def _prepare_financial_data(self) -> pd.DataFrame:
        """
        生データを分析用に前処理します。
        金額列のクリーンアップ、数値変換、振替行の除外を行います。

        Returns:
            pd.DataFrame: 前処理済みのデータフレーム。
        """
        # _processed_df が既に存在すれば、再処理せずそれを返します
        if self._processed_df is not None:
            return self._processed_df

        df = self.df.copy()  # 元のDataFrameを変更しないようにコピーを使用

        # '金額（円）'列が存在することを確認
        if self.AMOUNT_COLUMN not in df.columns:
            raise ValueError(f"DataFrameに '{self.AMOUNT_COLUMN}' 列が存在しません。")

        # --- データ前処理: 金額列のクリーンアップと数値変換 ---

        # (振替) が含まれる行を特定し、処理対象から除外 (NaNがあればFalse扱い)
        is_transfer_row = (
            df[self.AMOUNT_COLUMN].astype(str).str.contains(r"\(振替\)", na=False)
        )
        df_to_process = df[~is_transfer_row].copy()

        # 金額のカンマと(振替)文字列を取り除き、数値に変換
        # .astype(str) を使うことで、仮に元の列が数値型でも文字列として処理できます
        amount_cleaned = (
            df_to_process[self.AMOUNT_COLUMN]
            .astype(str)
            .str.replace(r"\(振替\)", "", regex=True)
            .str.replace(",", "", regex=False)
        )

        # 数値への変換を試みる。変換できない場合はNaNとする。
        df_processed = df_to_process.copy()  # NaN処理の前にコピー
        df_processed[self.AMOUNT_NUMERIC_COLUMN] = pd.to_numeric(
            amount_cleaned, errors="coerce"
        )

        # 数値変換できなかった（NaNになった）行は分析から除外する（データエラーの可能性）
        # 元のインデックスをリセットしたい場合は .reset_index(drop=True) を追加
        df_processed = df_processed.dropna(subset=[self.AMOUNT_NUMERIC_COLUMN]).copy()

        # 処理済みDataFrameを属性に保存しておくと、再呼び出し時に高速
        self._processed_df = df_processed

        return df_processed

    def calculate_monthly_summary(self) -> dict:
        """
        ステップ1: 基本集計を実行します。
        前処理済みのデータを使用し、収入合計、支出合計、収支を計算します。

        Returns:
            dict: 収入、支出、収支を含む辞書。
        """
        # 前処理済みのデータフレームを取得
        df_processed = self._prepare_financial_data()

        # --- 基本集計 ---
        # 収入の合計 (金額が正の値の行)
        income_total = df_processed[df_processed[self.AMOUNT_NUMERIC_COLUMN] > 0][
            self.AMOUNT_NUMERIC_COLUMN
        ].sum()
        # 支出の合計 (金額が負の値の行の合計。結果は負の値)
        expense_total_negative = df_processed[
            df_processed[self.AMOUNT_NUMERIC_COLUMN] < 0
        ][self.AMOUNT_NUMERIC_COLUMN].sum()
        expense_abs_total = abs(expense_total_negative)
        balance = income_total + expense_total_negative
        return {
            "income_total": income_total,
            "expense_total": expense_abs_total,  # 支出額として絶対値
            "balance": balance,
        }

    def analyze(self):
        """
        家計分析の主要なステップを実行し、レポートを生成します。
        これは最終的にレポートを生成するメソッドになるでしょう。
        """
        summary = self.calculate_monthly_summary()
