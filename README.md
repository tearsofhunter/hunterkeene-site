# hunterkeene-site

Portfolio site for hunterkeene.com.

- `content.json`: every project, section and news item
- `images/<project-slug>/`: photos for each project
- `assets/`: stylesheet and script
- `build.py`: turns `content.json` into the HTML pages (`python3 build.py`)

The `.html` files in the root are generated. Edit `content.json`, then rebuild.

## Adding a project image

In `content.json`, add to the project's `images` list:

```json
{ "src": "images/gothic-folly/01.jpg", "caption": "", "size": "full" }
```

`size` is `"full"` (whole width) or `"half"` (two side by side).
