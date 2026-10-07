# AutoArch AI execution

Run all commands from PCCOE_KinjalHeda_123B1F048_CS1_AIML using Python 3.11 or newer.

```bash
python Code/app.py
python Code/cli.py ask --question "What is the period of VehicleSpeed?" --version v2
python Code/scripts/evaluate.py --output Evaluation_Results/student_verified_run
python -m unittest discover -s Code/tests -v
```

Open http://127.0.0.1:8000 after starting the application. Stop with Ctrl+C. Default Markdown ingestion, CLI, HTTP service and evaluation use the Python standard library and no internet or external model API. Optional text PDF support needs pypdf 6.10.0 from requirements.txt.

engine.py implements ingestion, TF-IDF cosine retrieval, extractive cited answers, record parsing, graph impact, revision comparison and consistency rules. server.py serves the local UI and JSON APIs. cli.py uses the same engine. scripts/ contains input validation, index export, evaluation, synthetic input creation and optional local model configuration. tests/ contains 19 unit/integration checks.

The measured backend is extractive. No pretrained model run, graphical browser verification or Docker execution is claimed. Ollama setup is optional and requires separate evaluation; see Model_Prompts_Config/LOCAL_MODEL_SETUP.md. All outputs require engineering review.
