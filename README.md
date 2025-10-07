# Subsonic Proxy

A lightweight, containerized API proxy that acts as a bridge for Subsonic-compatible servers like Navidrome. It's designed to simplify fetching library statistics for use in modern dashboard widgets like Glance, which cannot handle Subsonic's dynamic authentication model on their own.

This service handles the complex salt-and-token authentication required by the Subsonic API and exposes simple, clean JSON endpoints that are easy to consume.

## Table of Contents

- [Subsonic Proxy](#subsonic-proxy)
  - [Table of Contents](#table-of-contents)
  - [Deployment Guide](#deployment-guide)
    - [Prerequisites](#prerequisites)
    - [Instructions](#instructions)
  - [The Problem Solved](#the-problem-solved)
  - [Features](#features)
  - [API Endpoints](#api-endpoints)
  - [Glance Widget Integration](#glance-widget-integration)
    - [Glance Setup](#glance-setup)
    - [Glance Secrets](#glance-secrets)
    - [Widget Configuration](#widget-configuration)

## Deployment Guide

This project is designed to be deployed as a Docker container.

### Prerequisites

- Docker and Docker Compose installed on your server.
- A running Subsonic-compatible server (e.g., Navidrome).
- A dedicated user created in your Subsonic server specifically for this proxy. For security, it is **strongly recommended** to use a non-admin user with a long, secure password.

### Instructions

1. **Create a `docker-compose.yml` File**

   On your server, create a directory for the service (e.g., `~/docker/subsonic-proxy`) and place the following `docker-compose.yml` file inside.

   ```yaml
   version: "3.8"

   services:
     subsonic-proxy:
       image: ghcr.io/somecodecat/subsonic-proxy:latest
       container_name: subsonic-proxy
       restart: unless-stopped
       ports:
         - "9876:8000" # Exposes the proxy on port 9876
       environment:
         - SUBSONIC_URL=${SUBSONIC_URL}
         - SUBSONIC_USERNAME=${SUBSONIC_USERNAME}
         - SUBSONIC_PASSWORD=${SUBSONIC_PASSWORD}
         - SUBSONIC_PROXY_API_KEY=${SUBSONIC_PROXY_API_KEY}
         - CACHE_TIMEOUT_SECONDS=${CACHE_TIMEOUT_SECONDS:-900}
   ```

2. **Set Environment Variables**

   This service is configured using environment variables. You must provide these to the container. A common method is to create a `.env` file in the same directory as your `docker-compose.yml` file.

   Create a file named `.env` with the following content, replacing the placeholder values:

   ```env
   # .env file
   # The internal or external URL for your Subsonic/Navidrome server.
   # The proxy needs this to communicate with your server.
   SUBSONIC_URL="http://your-navidrome-url:4533"

   SUBSONIC_USERNAME="your-api-user"
   SUBSONIC_PASSWORD="your-long-and-secret-password"
   SUBSONIC_PROXY_API_KEY="a-very-strong-random-key-for-the-proxy"

   # Optional: Set cache timeout in seconds (default is 900s / 15m)
   CACHE_TIMEOUT_SECONDS=900
   ```

   **Security Note**: The `SUBSONIC_PROXY_API_KEY` is a secret key you create. It's used to protect your proxy from unauthorized access. Make it long and random.

3. **Run with Docker Compose**

   From the directory containing your `docker-compose.yml` and `.env` files, pull the image and start the service:

   ```bash
   docker-compose pull
   docker-compose up -d
   ```

   The proxy service will now be running and accessible at `http://localhost:9876` (or whichever host and port you configure).

## The Problem Solved

Modern dashboard widgets often expect simple REST APIs that authenticate with a static header or token. The Subsonic API, however, requires a dynamic token to be generated for every single request: a random salt is created, appended to the password, and the md5 hash of the result is sent as a token.

This proxy encapsulates that entire logic, allowing any simple HTTP client to get data from a Subsonic server without needing to implement the complex and stateful authentication scheme.

## Features

- **Simple JSON Endpoints**: Provides easy-to-use endpoints for library statistics and detailed lists.
- **Handles Subsonic Auth**: Manages all salt-and-token authentication automatically.
- **Secure**: Protects your proxy endpoints with a required API key.
- **Performant**: Caches Subsonic API responses to reduce load and improve speed. Cache duration is configurable.
- **Containerized**: Runs as a minimal and efficient Docker container using Python and Flask.
- **Advanced Glance Widget**: Comes with a feature-rich Glance widget template that includes:
  - Interactive tooltips on hover to browse artists, albums, and songs.
  - Client-side search and sorting within tooltips.
  - Dynamic links that take you directly to the item in your Subsonic server.
  - Highly configurable to enable/disable features.

## API Endpoints

The proxy provides the following simple endpoints. All endpoints require the `X-Api-Key` header to be set to your `SUBSONIC_PROXY_API_KEY`.

- `GET /stats`: Returns the total counts of artists, albums, and songs.
- `GET /artists`: Returns a sorted list of all artists.
- `GET /albums`: Returns a sorted list of all albums with associated artist info.
- `GET /songs`: Returns a sorted list of all songs in the library.
- `GET /config`: Returns the base URL of the configured Subsonic instance, used for building dynamic links.

## Glance Widget Integration

This widget is designed for the [Glance Dashboard](https://github.com/glanceapp/glance/). It provides a summary of your library and includes interactive tooltips for browsing artists, albums, and songs directly from your dashboard.

### Glance Setup

Before adding the widget, you need to have Glance installed and running. For detailed instructions on setting up Glance, please refer to the [official documentation](https://github.com/glanceapp/glance).

### Glance Secrets

First, ensure you have the following secrets defined in your Glance environment. These should match the values from your `.env` file.

- `SUBSONIC_PROXY_URL`: The full URL of this proxy service (e.g., `http://192.168.1.100:9876`). This can be an internal or external URL, as long as your Glance instance can reach it.
- `SUBSONIC_PROXY_API_KEY`: The secret API key you created for the proxy.
- `SUBSONIC_SERVER_URL`: The base URL of your actual Subsonic/Navidrome server (e.g., `http://192.168.1.100:4533`). This should be an **external URL** if you want to be able to click links in the widget and open them from anywhere. If you only access your dashboard locally, an internal URL is fine.

### Widget Configuration

Add the following widget to your `glance.yml` file.

```yaml
- type: custom-api
  hide-header: true
  title: Navidrome Library
  cache: 1h
  url: ${SUBSONIC_PROXY_URL}/stats
  headers:
    X-Api-Key: ${SUBSONIC_PROXY_API_KEY}
  subrequests:
    artists:
      url: ${SUBSONIC_PROXY_URL}/artists
      headers:
        X-Api-Key: ${SUBSONIC_PROXY_API_KEY}
    albums:
      url: ${SUBSONIC_PROXY_URL}/albums
      headers:
        X-Api-Key: ${SUBSONIC_PROXY_API_KEY}
    songs:
      url: ${SUBSONIC_PROXY_URL}/songs
      headers:
        X-Api-Key: ${SUBSONIC_PROXY_API_KEY}

  options:
    # --- Main Feature Toggles ---
    hover_enabled: true # Enable/disable all hover tooltips
    main_links_enabled: true # Make main stat blocks clickable to open Subsonic

    # --- Tooltip Feature Toggles ---
    search_enabled: true # Show a search bar in tooltips
    sort_enabled: true # Show a sort button in tooltips
    tooltip_links_enabled: true # Make items inside tooltips clickable
    context_text_enabled: true # Show context (e.g., artist for albums, album for songs)

    # --- Required for Links ---
    subsonic_server_url: ${SUBSONIC_SERVER_URL}

  template: |
    {{- /* Widget Configuration */ -}}
    {{- $baseURL := .Options.StringOr "subsonic_server_url" "#" -}}
    {{- $hoverEnabled := .Options.BoolOr "hover_enabled" true -}}
    {{- $mainLinksEnabled := .Options.BoolOr "main_links_enabled" true -}}
    {{- $searchEnabled := .Options.BoolOr "search_enabled" true -}}
    {{- $sortEnabled := .Options.BoolOr "sort_enabled" true -}}
    {{- $tooltipLinksEnabled := .Options.BoolOr "tooltip_links_enabled" true -}}
    {{- $contextEnabled := .Options.BoolOr "context_text_enabled" true -}}
    <style>
      .stat-container > * {
        text-decoration: none; color: inherit; display: block; border-radius: 6px;
        transition: background-color 0.2s; flex: 1; margin: 0 4px;
      }
      .stat-link { cursor: pointer; }
      .stat-link:hover { background-color: var(--color-background-hover); }
      .stat-block { position: relative; {{ if $hoverEnabled }}cursor: pointer;{{ end }} }
      .tooltip {
        visibility: hidden; opacity: 0; position: fixed;
        width: 300px; max-height: 308px; overflow-y: hidden;
        display: flex; flex-direction: column;
        background-color: var(--color-background); color: var(--color-text);
        border: 1px solid var(--color-border); border-radius: 6px;
        z-index: 999; transition: opacity 0.2s; box-shadow: 0 4px 6px rgba(0,0,0,0.3);
      }
      .tooltip.show { visibility: visible; opacity: 1; }
      .tooltip-header {
        display: flex; align-items: center; gap: 8px;
        padding: 4px 8px; border-bottom: 1px solid var(--color-border);
        flex-shrink: 0; background-color: var(--color-background);
        position: sticky; top: 0; z-index: 1;
      }
      .tooltip-search {
        flex-grow: 1; background-color: var(--color-interactive-background);
        color: var(--color-text); border: 1px solid var(--color-border);
        border-radius: 4px; padding: 2px 6px; font-size: 0.9em;
      }
      .tooltip-header button {
        background-color: var(--color-interactive-background); color: var(--color-text);
        border: 1px solid var(--color-border); border-radius: 4px;
        padding: 2px 8px; font-size: 0.8em; cursor: pointer; white-space: nowrap;
      }
      .tooltip-header button:hover { background-color: var(--color-interactive-background-hover); }
      .tooltip-content { padding: 8px; font-size: 0.9em; overflow-y: auto; }
      .tooltip-content ul { list-style: none; padding: 0; margin: 0; }
      .tooltip-content li {
        display: flex; justify-content: space-between; align-items: center;
        padding: 5px 4px; border-bottom: 1px solid var(--color-border-subtle); border-radius: 3px;
      }
      .tooltip-content li:last-child { border-bottom: none; }
      .tooltip-content li:hover { background-color: var(--color-background-hover); }
      .tooltip-content a { color: inherit; text-decoration: none; }
      .tooltip-content a:hover { text-decoration: underline; }
      .tooltip-content .full-width-link, .tooltip-content .item-link {
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex-grow: 1;
      }
      .tooltip-content .context-link, .tooltip-content .context-text {
        font-size: 0.9em; opacity: 0.7; margin-left: 10px;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex-shrink: 0;
      }
    </style>

    <img src=x style="display:none" onerror="
      // --- Global State & Config ---
      window.hoverIsEnabled = {{ $hoverEnabled }};
      window.tooltipState = { hideTimeout: null, currentTooltip: null, sortDir: 'asc' };

      // --- Helper Functions ---
      window.filterList = function(type) {
        const searchTerm = document.getElementById(type + '-search').value.toLowerCase();
        const items = document.querySelectorAll('#' + type + '-tooltip ul li');
        items.forEach(li => {
          li.style.display = li.textContent.toLowerCase().includes(searchTerm) ? 'flex' : 'none';
        });
      };

      window.sortList = function(type) {
        const ul = document.querySelector('#' + type + '-tooltip ul');
        if (!ul) return;
        const items = Array.from(ul.querySelectorAll('li'));
        window.tooltipState.sortDir = window.tooltipState.sortDir === 'asc' ? 'desc' : 'asc';
        items.sort((a, b) => {
          const textA = a.textContent.trim().toLowerCase();
          const textB = b.textContent.trim().toLowerCase();
          return window.tooltipState.sortDir === 'asc' ? textA.localeCompare(textB) : textB.localeCompare(textA);
        });
        ul.innerHTML = '';
        items.forEach(li => ul.appendChild(li));
        document.getElementById(type + '-sort-btn').textContent = window.tooltipState.sortDir === 'asc' ? 'A-Z' : 'Z-A';
      };

      // --- Tooltip Management ---
      window.showTooltip = function(type, element) {
        if (!window.hoverIsEnabled) return;
        if (window.tooltipState.currentTooltip) window.tooltipState.currentTooltip.classList.remove('show');
        clearTimeout(window.tooltipState.hideTimeout);
        const tooltip = document.getElementById(type + '-tooltip');
        if (!tooltip) return;

        // Reset search field on show
        const searchInput = document.getElementById(type + '-search');
        if (searchInput && searchInput.value) {
          searchInput.value = '';
          filterList(type);
        }

        const rect = element.getBoundingClientRect(), tooltipWidth = 300, tooltipHeight = 308, margin = 8;
        let top = rect.bottom + margin, left = rect.left + (rect.width / 2) - (tooltipWidth / 2);
        if (top + tooltipHeight > window.innerHeight) { top = rect.top - tooltipHeight - margin; }
        if (left < margin) { left = margin; } else if (left + tooltipWidth > window.innerWidth - margin) { left = window.innerWidth - tooltipWidth - margin; }

        tooltip.style.top = top + 'px';
        tooltip.style.left = left + 'px';
        tooltip.classList.add('show');
        window.tooltipState.currentTooltip = tooltip;
      };

      window.hideTooltip = function() {
        window.tooltipState.hideTimeout = setTimeout(() => {
          if (window.tooltipState.currentTooltip) {
            window.tooltipState.currentTooltip.classList.remove('show');
            window.tooltipState.currentTooltip = null;
          }
        }, 300);
      };
    ">

    <!-- Main Stat Blocks -->
    <div class="flex justify-around text-center stat-container">
      <div class="stat-link" {{ if $hoverEnabled }}onmouseenter="showTooltip('artists', this)" onmouseleave="hideTooltip()"{{ end }}>
        {{ if $mainLinksEnabled }}<a href="{{ $baseURL }}/app/#/artist" target="_blank" style="text-decoration: none; color: inherit;">{{ end }}
          <div class="stat-block">
            <div class="color-highlight size-h3">{{ .JSON.Int `artistCount` | formatNumber }}</div>
            <div class="size-h6">ARTISTS</div>
          </div>
        {{ if $mainLinksEnabled }}</a>{{ end }}
      </div>

      <div class="stat-link" {{ if $hoverEnabled }}onmouseenter="showTooltip('albums', this)" onmouseleave="hideTooltip()"{{ end }}>
        {{ if $mainLinksEnabled }}<a href="{{ $baseURL }}/app/#/album/all" target="_blank" style="text-decoration: none; color: inherit;">{{ end }}
          <div class="stat-block">
            <div class="color-highlight size-h3">{{ .JSON.Int `albumCount` | formatNumber }}</div>
            <div class="size-h6">ALBUMS</div>
          </div>
        {{ if $mainLinksEnabled }}</a>{{ end }}
      </div>

      <div class="stat-link" {{ if $hoverEnabled }}onmouseenter="showTooltip('songs', this)" onmouseleave="hideTooltip()"{{ end }}>
        {{ if $mainLinksEnabled }}<a href="{{ $baseURL }}/app/#/song" target="_blank" style="text-decoration: none; color: inherit;">{{ end }}
          <div class="stat-block">
            <div class="color-highlight size-h3">{{ .JSON.Int `songCount` | formatNumber }}</div>
            <div class="size-h6">SONGS</div>
          </div>
        {{ if $mainLinksEnabled }}</a>{{ end }}
      </div>
    </div>

    <!-- Tooltip Definitions -->
    {{ if $hoverEnabled }}
    <div id="artists-tooltip" class="tooltip" onmouseenter="clearTimeout(window.tooltipState.hideTimeout)" onmouseleave="hideTooltip()">
      {{ if or $searchEnabled $sortEnabled }}<div class="tooltip-header">{{ if $searchEnabled }}<input type="text" id="artists-search" class="tooltip-search" placeholder="Search..." onkeyup="filterList('artists')">{{ end }}{{ if $sortEnabled }}<button id="artists-sort-btn" onclick="sortList('artists')">A-Z</button>{{ end }}</div>{{ end }}
      <div class="tooltip-content">
        <ul>
          {{- range (.Subrequest "artists").JSON.Value }}
            <li>
              {{- if $tooltipLinksEnabled }}
                <a href="{{ $baseURL }}/#/artist/{{ index . "id" }}/show" target="_blank" class="full-width-link"><span class="item-name">{{ index . "name" }}</span></a>
              {{- else }}
                <span class="full-width-link item-name">{{ index . "name" }}</span>
              {{- end }}
            </li>
          {{- end }}
        </ul>
      </div>
    </div>

    <div id="albums-tooltip" class="tooltip" onmouseenter="clearTimeout(window.tooltipState.hideTimeout)" onmouseleave="hideTooltip()">
      {{ if or $searchEnabled $sortEnabled }}<div class="tooltip-header">{{ if $searchEnabled }}<input type="text" id="albums-search" class="tooltip-search" placeholder="Search..." onkeyup="filterList('albums')">{{ end }}{{ if $sortEnabled }}<button id="albums-sort-btn" onclick="sortList('albums')">A-Z</button>{{ end }}</div>{{ end }}
      <div class="tooltip-content">
        <ul>
          {{- range (.Subrequest "albums").JSON.Value }}
            <li>
              {{- if $tooltipLinksEnabled }}<a class="item-link" href="{{ $baseURL }}/#/album/{{ index . "id" }}/show" target="_blank">{{ index . "name" }}</a>{{ else }}<span class="item-link">{{ index . "name" }}</span>{{ end -}}
              {{- if and $contextEnabled (index . "artistId") }}
                {{- if $tooltipLinksEnabled }}<a class="context-link" href="{{ $baseURL }}/#/artist/{{ index . "artistId" }}/show" target="_blank">{{ index . "artistName" }}</a>{{ else }}<span class="context-text">{{ index . "artistName" }}</span>{{ end -}}
              {{- end }}
            </li>
          {{- end }}
        </ul>
      </div>
    </div>

    <div id="songs-tooltip" class="tooltip" onmouseenter="clearTimeout(window.tooltipState.hideTimeout)" onmouseleave="hideTooltip()">
      {{ if or $searchEnabled $sortEnabled }}<div class="tooltip-header">{{ if $searchEnabled }}<input type="text" id="songs-search" class="tooltip-search" placeholder="Search..." onkeyup="filterList('songs')">{{ end }}{{ if $sortEnabled }}<button id="songs-sort-btn" onclick="sortList('songs')">A-Z</button>{{ end }}</div>{{ end }}
      <div class="tooltip-content">
        <ul>
          {{- range (.Subrequest "songs").JSON.Value }}
            <li>
              {{- if $tooltipLinksEnabled }}
                <a href="{{ $baseURL }}/#/album/{{ index . "albumId" }}/show" target="_blank" class="full-width-link">
                  <span class="item-name">{{ index . "name" }}</span>
                  {{- if and $contextEnabled (index . "context") }}<span class="context-text">{{ index . "context" }}</span>{{ end -}}
                </a>
              {{- else }}
                <span class="full-width-link">
                  <span class="item-name">{{ index . "name" }}</span>
                  {{- if and $contextEnabled (index . "context") }}<span class="context-text">{{ index . "context" }}</span>{{ end -}}
                </span>
              {{- end }}
            </li>
          {{- end }}
        </ul>
      </div>
    </div>
    {{ end }}
```
