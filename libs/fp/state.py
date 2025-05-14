from typing_extensions import Any, Optional, TypedDict

import pandas as pd


class State(TypedDict):
    # Step1：基本集計
    processed_df: pd.DataFrame
    income: int
    expense: int
    balance: int
    # Step2：初期カテゴリの分類と固定費・変動費の出力
    income_categories: list[str]
    expense_categories: list[str]
    fixed_expense_total: int
    variable_expense_total: int
    # Step3：未分類取引の処理と確認の出力
    unclassified_income_count: int
    unclassified_expense_count: int
    unclassified_income_total: int
    unclassified_expense_total: int
    # Step4：項目別の集計及び割合の出力
    category_summary: list[dict[str, Any]]
    # Step5：注目すべき支出の特定
    high_value_expenses: list[dict[str, Any]]
    frequent_locations: Optional[list[dict[str, Any]]]
    recurring_expenses: Optional[list[dict[str, Any]]]
    # Step6：家計バランスと貯蓄可能性の評価
    balance_evaluation: str
    fixed_variable_ratio_evaluation: str
    savings_potential_evaluation: str
    # Step7：家計改善のインサイト
    improvement_proposals: list[str]
    # Step8：分析レポートの生成[Markdown]
    final_report_text: str
    # Others
    analysis_month: str
