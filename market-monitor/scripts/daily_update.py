from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def run_step(description, script_name):

    print("\n" + "=" * 65)
    print(description)
    print("=" * 65)

    script_path = SCRIPTS / script_name

    subprocess.run(
        [sys.executable, str(script_path)],
        cwd=ROOT,
        check=True
    )

    print(f"\nCompleted: {description}")


def main():

    print("=" * 65)
    print("S&P 500 MARKET PREDICTOR")
    print("DAILY UPDATE")
    print("=" * 65)

    # 1. Collect market prices and indicators
    run_step(
        "STEP 1: Updating market prices",
        "update_market_data.py"
    )

    # 2. Collect CBOE Put/Call Ratio
    run_step(
        "STEP 2: Updating Put/Call Ratio",
        "update_put_call_ratio.py"
    )

    # 3. Rebuild historical features
    run_step(
        "STEP 3: Preparing feature history",
        "prepare_historical_dataset.py"
    )

    # 4. Evaluate previous predictions
    run_step(
        "STEP 4: Updating prediction outcomes",
        "update_prediction_outcomes.py"
    )

    # 5. Generate a new prediction
    run_step(
        "STEP 5: Generating prediction",
        "generate_prediction.py"
    )

    print("\n" + "=" * 65)
    print("DAILY UPDATE FINISHED")
    print("=" * 65)

    print(
        "\nThe application data and prediction history "
        "have been refreshed."
    )


if __name__ == "__main__":
    main()
