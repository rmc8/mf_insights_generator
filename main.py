import os
import pathlib
from datetime import datetime

import fire  # type: ignore
from dotenv import load_dotenv

from libs.mf import MoneyForwardMeClient


load_dotenv()
now = datetime.now()
this_dir = pathlib.Path(__file__).parent
output_dir = this_dir / "output" / f"{now:%Y%m%d%H%M%S}"


class Agent:
    def scrape(self, is_last_month: bool = True) -> pathlib.Path:
        mfmc = MoneyForwardMeClient(
            email=str(os.environ.get("MONEYFORWARD_EMAIL")),
            password=str(os.environ.get("MONEYFORWARD_PASSWORD")),
        )
        try:
            mfmc.login()
            df = mfmc.get_cf_data(is_last_month=is_last_month)
            output_path = output_dir / "mf_data.tsv"
            os.makedirs(output_dir, exist_ok=True)
            df.to_csv(output_path, sep="\t", index=False)
            return output_path
        finally:
            mfmc.close()

    def analyze(self, input_path: str):
        p = pathlib.Path(input_path)
        os.makedirs(output_dir, exist_ok=True)

    def run(self, is_last_month: bool = True):
        path = self.scrape(is_last_month=is_last_month)
        self.analyze(str(path))


def main():
    fire.Fire(Agent)


if __name__ == "__main__":
    main()
