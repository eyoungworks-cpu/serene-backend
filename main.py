from fastapi import FastAPI

app = FastAPI()

@app.get("/skills")
def get_skills():
    return [
        {"name": "Workflow Automation", "category": "Operations"},
        {"name": "Account Management", "category": "Integration"}
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
