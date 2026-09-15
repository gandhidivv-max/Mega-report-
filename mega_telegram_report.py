def generate_cinematic_dashboard_image(accounts_data, total_files, total_videos, target_count, total_bin):
    labels = [acc["name"] for acc in accounts_data]
    video_counts = [acc["videos"] for acc in accounts_data]

    chart_config = {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": "Videos",
                "data": video_counts,
                "backgroundColor": ["rgba(0, 242, 254, 0.85)", "rgba(225, 29, 115, 0.85)", "rgba(255, 154, 0, 0.85)"],
                "borderColor": ["#00f2fe", "#e11d73", "#ff9a00"],
                "borderWidth": 2,
                "borderRadius": 8,
                "datalabels": {
                    "align": "end",
                    "anchor": "end",
                    "color": "#ffffff",
                    "font": {"size": 16, "weight": "bold"}
                }
            }]
        },
        "options": {
            "plugins": {
                "title": {
                    "display": True,
                    "text": "🌌 MEGA CLOUD LIVE DASHBOARD",
                    "color": "#ffffff",
                    "font": {"size": 20, "weight": "bold"}
                },
                "subtitle": {
                    "display": True,
                    "text": f"📁 Total Files: {total_files}  |  🎬 Videos: {total_videos}/{target_count}  |  🗑️ Trash: {total_bin}",
                    "color": "#38bdf8",
                    "font": {"size": 14, "weight": "bold"},
                    "padding": {"bottom": 20}
                },
                "legend": {"display": False},
                "datalabels": {"display": True}
            },
            "scales": {
                "x": {
                    "ticks": {"color": "#a0aec0", "font": {"size": 14, "weight": "bold"}},
                    "grid": {"display": False}
                },
                "y": {
                    "ticks": {"color": "#a0aec0", "font": {"size": 12}},
                    "grid": {"color": "rgba(255, 255, 255, 0.1)"},
                    "grace": "15%"  # నంబర్లు ఇమేజ్ పైన కట్ అవ్వకుండా ఖాళీ స్థలం ఇస్తుంది
                }
            }
        }
    }

    # Data Labels Plugin Activation
    chart_config["plugins"] = ["chartjs-plugin-datalabels"]

    encoded_chart = urllib.parse.quote(json.dumps(chart_config))
    image_url = f"https://quickchart.io/chart?c={encoded_chart}&bkg=%230f172a&w=800&h=450&devicePixelRatio=2"
    return image_url
    
