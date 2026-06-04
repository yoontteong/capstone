from flask import Flask, render_template, request, session
from ai_scheduler import generate_ai_schedule
from checklist import get_jeju_weather, recommend_checklist
from schedule_editor import schedule_editor, normalize_schedule

app = Flask(__name__)
app.secret_key = "pinksole_secret_key"

app.register_blueprint(schedule_editor)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/checklist")
def checklist_page():
    return render_template("checklist.html")


@app.route("/checklist-result", methods=["POST"])
def checklist_result():
    travel_date = request.form.get("travel_date")
    stay = request.form.get("stay")
    outdoor = request.form.get("outdoor")

    weather = get_jeju_weather(travel_date)

    items = recommend_checklist(
        weather=weather,
        stay=stay,
        outdoor=outdoor
    )

    return render_template(
        "checklist_result.html",
        travel_date=travel_date,
        weather=weather,
        items=items
    )


@app.route("/ai-schedule", methods=["GET"])
def ai_schedule_form():
    return render_template("ai_schedule.html")


@app.route("/ai-schedule/result", methods=["POST"])
def ai_schedule_result():
    travel_period = request.form.get("travel_period")
    style = request.form.get("style")
    transport_type = request.form.get("transport_type")
    dog_size = request.form.get("dog_size")
    dog_personality = request.form.get("dog_personality")

    schedule, pattern = generate_ai_schedule(
        dog_size=dog_size,
        dog_personality=dog_personality,
        style=style,
        travel_period=travel_period,
        transport_type=transport_type
    )

    schedule = normalize_schedule(schedule)

    session["schedule"] = schedule
    session["pattern"] = pattern
    session["travel_info"] = {
        "travel_period": travel_period,
        "style": style,
        "transport_type": transport_type,
        "dog_size": dog_size,
        "dog_personality": dog_personality
    }

    return render_template(
        "ai_schedule_result.html",
        travel_period=travel_period,
        style=style,
        transport_type=transport_type,
        dog_size=dog_size,
        dog_personality=dog_personality,
        schedule=schedule,
        pattern=pattern
    )


#기록측정추가
@app.route("/activity")
def activity():
    return render_template("activity.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, ssl_context='adhoc')