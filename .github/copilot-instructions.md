# Copilot instructions for MathHacks2.0-TempName-

## Project overview
- This repository is a very small Python game/app built with Ursina.
- The entry point is `main.py`; it starts an Ursina app, creates a red cube and a terrain, then runs the app loop.
- The codebase is intentionally single-file and asset-light. No package structure, business logic separation, or build orchestration exists yet.
- The README is minimal; the project is effectively a small demo scene rather than a multi-module application.

## Build, test, and lint commands
- No formal build, test, or lint configuration was found in the repository.
- Use the active Python interpreter directly for local smoke checks:
  - `python -m py_compile main.py` to validate syntax
  - `python main.py` to launch the app
- There are no preconfigured test or lint commands to run in this repo as-is.

## High-level architecture
- `main.py` is the only code file and is responsible for the complete app bootstrap.
- The app is set up in one place:
  - `Ursina(...)` creates the runtime
  - `Entity(...)` adds the scene object(s)
  - `Terrain(...)` initializes the environment
  - `EditorCamera()` provides interactive camera movement
  - `app.run()` starts the main loop
- The project follows Ursina's immediate scene-construction pattern: instantiate objects directly in the module and let the framework manage their lifecycle.
- `Height Map PNG.png` appears to be an asset related to terrain generation or level height data; keep any future terrain-related asset usage centralized rather than scattering file paths across multiple files.

## Key conventions
- Keep the code minimal and script-like; this repository currently favors a single-file composition over abstraction.
- Use the Ursina API directly instead of wrapping it in helper classes unless the project grows beyond the demo structure.
- Preserve the startup pattern: initialize the runtime, add scene entities, and call `app.run()` once at the end.
- If the project expands, prefer a straightforward structure such as `main.py` for bootstrapping and a small set of helper modules rather than introducing heavier frameworks prematurely.

## Repo-specific notes
- There is no dependency manifest (`requirements.txt`, `pyproject.toml`, `setup.py`, or similar) in the repository snapshot.
- The application depends on the local Python environment and the Ursina package being installed in that environment.
