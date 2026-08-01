# Public Deployment

CareerProof AI is a state-light FastAPI application. All labor-market evidence is bundled with the repository, so the public build does not require an API key or external database.

## Recommended free option: Render

## One-click Render Blueprint

The public GitHub README includes a **Deploy to Render** button for `PandaExpress15/hackathon`. After the final code is pushed, click the button, sign in to Render, review the free web service defined by `render.yaml`, and approve the Blueprint. The service is configured for the Virginia region and checks `/api/health`.


Render can deploy the application directly from the public GitHub repository. The repository includes `render.yaml`, `Procfile`, and a production-compatible `app.py`.

### Dashboard deployment

1. Push the final project to the public GitHub repository.
2. Sign in to Render and create a **Web Service**.
3. Connect the CareerProof repository and select the `main` branch.
4. Use these settings if Render does not automatically read `render.yaml`:

   - Runtime: `Python 3`
   - Build command: `python -m pip install --upgrade pip && python -m pip install -r requirements.txt`
   - Start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - Health check path: `/api/health`
   - Instance type: `Free`

5. Deploy and wait for the status to become **Live**.
6. Open the generated public URL in a private browser window.
7. Test Home, Build My Path, Compare Lab, Evidence Passport, Judge Mode, safe refusal, and report export.

Render free web services can spin down after a period of inactivity. The first request after sleep can take longer while the service starts again. Do not wait until the presentation begins to wake the deployment.

## Blueprint deployment

The root `render.yaml` can be used as a Render Blueprint. It defines the free Python web service, build command, start command, and health check.

## Docker deployment

The root `Dockerfile` runs the same application on port 7860.

```bash

docker build -t careerproof-ai .
docker run --rm -p 7860:7860 careerproof-ai
```

Open `http://127.0.0.1:7860`.

## Hugging Face Docker Space preparation

A Space-specific README is included at `deploy/huggingface/README.md`. Docker Spaces require a repository README with `sdk: docker` and `app_port: 7860` in its YAML header. Account eligibility and plan requirements can change, so confirm the current Space creation rules before relying on it as the free submission host.

## Production behavior

- `app.py` binds to `0.0.0.0` by default.
- `PORT` is honored when supplied by a hosting platform.
- `/api/health` is available for health checks.
- No credentials are required.
- Saved plans and decision notes use browser local storage, not server persistence.
- The bundled official data is read-only during normal use.

## Public release checklist

- The public URL works in a private browser window.
- The deployment reports a successful `/api/health` response.
- Browser zoom is 100 percent and all information text remains readable.
- Judge Mode opens, resets, switches between Full and Quick modes, and reaches every stage.
- All live-feature launch buttons open the intended workspace.
- The Evidence Passport opens from a recommendation.
- The unsupported guarantee question is refused.
- The repository and submitted ZIP contain the same final code.
- No `.env`, token, password, or private dataset is present.
