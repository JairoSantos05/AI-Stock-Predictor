# AI Stock Direction Predictor

A Python machine learning project that uses historical stock data to predict next-day price direction and output a Buy / Hold / Don't Buy confidence score.

## Team Setup

### 1. Clone the Repository
```bash
git clone [https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git](https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git)
cd YOUR_REPO_NAME
```

### 2. Create and Activate a Virtual Environment
Make sure you have **Python 3.10+** installed.

**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```
*(If PowerShell blocks the script, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` once, then try activating again.)*

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

## Git Workflow (Important)
Do **not** push directly to `main`. Create your own branch before writing code:
```bash
git checkout -b your-branch-name
```
* **Data Pipeline:** `data-pipeline`
* **Modeling:** `modeling`
* **Evaluation & Docs:** `eval-docs`

Always pull the latest `main` before starting a new work session:
```bash
git checkout main
git pull origin main
```

## Running the Application
```bash
python main.py
```