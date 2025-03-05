import altair as alt

# Spotify brand colors
SPOTIFY_GREEN = '#1DB954'

# Bar chart base configuration with proper label display
BAR_CHART_BASE = {
    "mark": {"type": "bar", "color": SPOTIFY_GREEN},
    "encoding": {
        "text": alt.Text("count:Q"),  # For potential text labels
    },
    "height": {"step": 25}  # Ensure enough height per bar
}

# Chart configurations
CHART_CONFIGS = {
    "top_tracks": {
        **BAR_CHART_BASE,
        "encoding": {
            "x": alt.X('total_ms:Q', title='Listening Time (ms)'),
            "y": alt.Y('track_label:N', 
                      title=None, 
                      sort='-x', 
                      axis=alt.Axis(minExtent=200)),
            "tooltip": ["track_label:N", "artist:N", "total_ms:Q", "play_count:Q"]
        }
    },
    "top_artists": {
        **BAR_CHART_BASE,
        "encoding": {
            "x": alt.X("total_ms:Q", title="Total Listening Time (ms)"),
            "y": alt.Y("artist:N", 
                      sort="-x", 
                      title="Artist", 
                      axis=alt.Axis(minExtent=150)),
            "tooltip": ["artist:N", "total_ms:Q", "play_count:Q", "unique_tracks:Q"]
        }
    },
    "top_albums": {
        **BAR_CHART_BASE,
        "encoding": {
            "x": alt.X("total_ms:Q", title="Total Listening Time (ms)"),
            "y": alt.Y("album:N", 
                      sort="-x", 
                      title="Album", 
                      axis=alt.Axis(minExtent=200)),
            "tooltip": ["album:N", "artist:N", "total_ms:Q", "play_count:Q", "unique_tracks:Q"]
        }
    },
    "top_genres": {
        **BAR_CHART_BASE,
        "encoding": {
            "x": alt.X("total_ms:Q", title="Total Listening Time (ms)"),
            "y": alt.Y("genre:N", 
                      sort="-x", 
                      title="Genre", 
                      axis=alt.Axis(minExtent=120)),
            "tooltip": ["genre:N", "total_ms:Q", "play_count:Q", "unique_tracks:Q"]
        }
    },
    "artist_popularity": {
        "mark": "circle",
        "encoding": {
            "x": alt.X('artist_popularity:Q', title='Artist Popularity', scale=alt.Scale(domain=[0, 100])),
            "y": alt.Y('play_count:Q', title='Number of Plays'),
            "size": alt.Size('play_count:Q', scale=alt.Scale(range=[100, 1000])),
            "color": alt.Color('artist_popularity:Q', scale=alt.Scale(scheme='viridis')),
            "tooltip": ["artist:N", "artist_popularity:Q", "play_count:Q"]
        }
    },
    "punch_card": {
        "mark": "circle",
        "encoding": {
            "x": alt.X("hour:O", title="Hour of Day"),
            "y": alt.Y("weekday:O", title="Day of Week", sort=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]),
            "size": alt.Size("count:Q", scale=alt.Scale(range=[50, 500])),
            "color": alt.Color("avg_duration_min:Q", scale=alt.Scale(scheme='viridis')),
            "tooltip": ["weekday:O", "hour:O", "count:Q", "avg_duration_min:Q"]
        }
    },
    "genre_evolution": {
        "mark": "area",
        "encoding": {
            "x": alt.X("period:T", title="Time"),
            "y": alt.Y("plays:Q", stack="normalize", title="Proportion of Plays"),
            "color": alt.Color("genre:N", scale=alt.Scale(scheme='category20')),
            "tooltip": ["period:T", "genre:N", "plays:Q", "proportion:Q"]
        }
    },
    "polar_hour": {
        "mark": {"type": "arc", "innerRadius": 20},
        "encoding": {
            "theta": alt.Theta("hour:O", scale=alt.Scale(domain=list(range(24)))),
            "radius": alt.Radius("count:Q", scale=alt.Scale(type="sqrt")),
            "color": alt.Color("count:Q", scale=alt.Scale(scheme='viridis')),
            "tooltip": ["hour:O", "count:Q"]
        }
    },
    "ridgeline_year": { #Needs work
        "mark": {"type": "area", "interpolate": 'monotone', "fillOpacity": 0.6, "stroke":'lightgray', "strokeWidth":0.5},
        "encoding": {
            "x": alt.X('year:Q', title='Release Year', scale = alt.Scale(domain=[1950,2024])),
            "y": alt.Y('year:N', title='Year', axis=alt.Axis(domain=False, tickSize=0), sort='descending'),
            "color": alt.Color('year:N', scale=alt.Scale(scheme='viridis'), legend=None),
            "size": alt.Size('count:Q', title='Number of Tracks', scale = alt.Scale(range=[0,50])),
            "tooltip" : ['year:Q', 'density:Q']
        },
        "transform": [
            {"density": 'year',
             "as": ['year', 'density'],
             "groupby": ['year'],
             "steps": 100,
             "extent": [1950, 2024]} #Adjust if needed
        ]
    },
    "remix_pie": {
        "mark": {"type": "arc", "innerRadius": 50},
        "encoding":{
            "theta": alt.Theta("count:Q"),
            "color": alt.Color("is_remix:N", scale=alt.Scale(domain=['Original', 'Remix'], range=['#1db954', '#ff6b6b'])),
            "tooltip": ["is_remix:N", "count:Q", "percentage:Q"]
        }
    },
    "skip_pie": {
        "mark": {"type": "arc", "innerRadius": 50},
        "encoding": {
            "theta": alt.Theta("count:Q"),
            "color": alt.Color("skipped:N", scale=alt.Scale(domain=['Completed', 'Skipped'], range=['#1db954', '#ff6b6b'])),
            "tooltip": ["skipped:N", "count:Q", "percentage:Q"]
        }
    },
    "listening_trends_scatter": {
        "mark": "circle",
        "encoding":{
            "x": alt.X('hour:Q', title='Hour of Day'),
            "y": alt.Y('weekday:O', title='Day of Week'),
            "size": alt.Size('count:Q', legend=alt.Legend(title='Plays')),
            "color": alt.Color('avg_duration_min:Q',
                               scale=alt.Scale(scheme='viridis'),
                               legend=alt.Legend(title='Avg Duration (min)')),
            "tooltip": ['weekday:O', 'hour:Q', 'count:Q', 'avg_duration_min:Q']
        }
    },
    "genre_diversity": {
        "mark": {"type": "line", "point": True, "color": SPOTIFY_GREEN},
        "encoding": {
            "x": alt.X("period:T", title="Time Period"),
            "y": alt.Y("genre_count:Q", title="Unique Genres"),
            "tooltip": ["period:T", "genre_count:Q"]
        }
    },
    "album_completion": {
        "mark": {"type": "bar", "color": SPOTIFY_GREEN},
        "encoding": {
            "x": alt.X("completion:Q", title="Completion Rate (%)"),
            "y": alt.Y("album:N", sort="-x", title="Album"),
            "text": alt.Text("completion:Q", format='.1f'),
            "tooltip": ["album:N", "artist:N", "completion:Q", "played_tracks:Q", "total_tracks:Q"]
        }
    }
}