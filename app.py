from flask import Flask, render_template, request
from ai_scheduler import generate_ai_schedule

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("ai_schedule.html")


@app.route("/ai-schedule", methods=["GET"])
def ai_schedule_form():
    return render_template("ai_schedule.html")


@app.route("/ai-schedule/result", methods=["POST"])
def ai_schedule_result():
    travel_period = request.form.get("travel_period")
    style = request.form.get("style")
    dog_size = request.form.get("dog_size")
    dog_personality = request.form.get("dog_personality")

    schedule, pattern = generate_ai_schedule(
        dog_size=dog_size,
        dog_personality=dog_personality,
        style=style
    )

    return render_template(
        "ai_schedule_result.html",
        travel_period=travel_period,
        style=style,
        dog_size=dog_size,
        dog_personality=dog_personality,
        schedule=schedule,
        pattern=pattern
    )


if __name__ == "__main__":
    app.run(debug=True)