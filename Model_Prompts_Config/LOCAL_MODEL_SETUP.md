# Optional local pretrained-model setup

**Not executed in the build environment. These are candidate choices, not measured models.** The core package is a tested offline extractive baseline; the notice's pretrained-model requirement remains outstanding.

1. Use the selected local model and synthetic corpus; document its exact version and separate measured results.
2. Install Ollama from its official source and start its local service. Initial installation/model downloads require internet.
3. Pull the candidates only if accepted: `ollama pull qwen2.5:1.5b` and `ollama pull nomic-embed-text:v1.5`.
4. Run `python Code/scripts/configure_local_model.py`. It checks installed model names on loopback, records their digests and Ollama version, saves the baseline config and activates the candidate config. It does **not** certify model quality.
5. Restart the app and execute a sample query. Confirm that responses contain allowed citation IDs and supporting exact evidence quotes. Read the original source to review claim meaning.
6. Run `python Code/scripts/evaluate.py --output Evaluation_Results/local_pretrained_run`. This uses the same references and writes separate results, preserving the supplied baseline evidence. Check failures as well as successes. Run the UI and repeat browser verification locally.
7. Add your actual installed model identifiers/digests, hardware, timestamps, prompts, results and limitations to the report/synopsis. Record any method change. Record a demonstration of that exact configuration. Never present the supplied baseline metrics/video as results of these models.

To restore the supplied baseline: copy model_config_extractive_backup.json to model_config.json and restart. The candidate embed threshold is 0.25; treat it as an unvalidated setting requiring evaluation. No hardcoded question answers or hidden cloud fallback are used.

Adapter references: https://docs.ollama.com/api ; https://ollama.com/library/qwen2.5:1.5b ; https://ollama.com/library/nomic-embed-text:v1.5 . Capture installed digests because named tags alone are not immutable versions.
