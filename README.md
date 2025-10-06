# Subsonic Proxy

A lightweight, containerized API proxy that acts as a bridge for Subsonic-compatible servers like Navidrome. It's designed to simplify fetching library statistics for use in modern dashboard widgets like Glance, which cannot handle Subsonic's dynamic authentication model on their own.

This service handles the complex salt-and-token authentication required by the Subsonic API and exposes simple, clean JSON endpoints that are easy to consume.

## The Problem Solved

Modern dashboard widgets often expect simple REST APIs that authenticate with a static header or token. The Subsonic API, however, requires a dynamic token to be generated for every single request: a random salt is created, appended to the password, and the md5 hash of the result is sent as a token.

This proxy encapsulates that entire logic, allowing any simple HTTP client to get data from a Subsonic server without needing to implement the complex and stateful authentication scheme.

## Features

- Simple JSON Endpoints: Provides easy-to-use endpoints for library statistics and detailed lists.
- Handles Subsonic Auth: Manages all salt-and-token authentication automatically.
- Containerized: Runs as a minimal and efficient Docker container using Python and Flask.

## Deployment Guide

This project is designed to be deployed as a Docker container.

### Prerequisites

- Docker and Docker Compose installed on your server.
- A running Subsonic-compatible server (e.g., Navidrome).
- (Optional) A dedicated, non-admin user created in your Subsonic server specifically for this proxy, with a long, secure password.

### Instructions

1. **Create a `docker-compose.yml` File**

   On your server, create a directory for the service (e.g., `~/docker/subsonic-proxy`) and place the following `docker-compose.yml` file inside.

   ```yaml
   version: "3.8"

   services:
     subsonic-proxy:
       image: ghcr.io/SomeCodecat/subsonic-proxy:latest
       container_name: subsonic-proxy
       restart: unless-stopped
       ports:
         - "9876:9876"
       environment:
         - NAVIDROME_URL=${NAVIDROME_URL}
         - NAVIDROME_USERNAME=${NAVIDROME_USERNAME}
         - NAVIDROME_API_KEY=${NAVIDROME_API_KEY}
   ```

2. **Run with Docker Compose**

   From the directory containing your `docker-compose.yml` file, pull the image from the registry and start the service:

   ```bash
   docker-compose pull
   docker-compose up -d
   ```

   The proxy service will now be running and accessible at `http://localhost:9876` (or whichever port you configure).

## API Endpoints

The proxy provides the following simple endpoints:

- `GET /stats`: Returns the total counts of artists, albums, and songs.
- `GET /artists`: Returns a list of all artists.
- `GET /albums`: Returns a list of all albums with associated artist info.
- `GET /songs`: Returns a list of all songs with associated album info.
- `GET /config`: Returns the base URL of the configured Navidrome instance.

## Glance Widget Integration

Add the following widget to your `glance.yml` file. Ensure you have a `SUBSONIC_PROXY_URL` secret defined in your Glance environment that points to this running service (e.g., `SUBSONIC_PROXY_URL=http://127.0.0.1:9876`).

```yaml
- type: custom-api
  hide-header: true
  title: Navidrome Library
  cache: 1h
  url: ${secret:SUBSONIC_PROXY_URL}/stats

  options:
    list_cache_minutes: 15
    hover_enabled: true

  template: |
    <style>
      .stat-link {
        text-decoration: none;
        color: inherit;
        display: block;
        border-radius: 6px;
        transition: background-color 0.2s;
        flex: 1;
        margin: 0 4px;
      }
      .stat-link:hover {
        background-color: var(--color-background-hover);
      }
      .stat-block { 
        position: relative; 
        cursor: pointer;
      }
      .tooltip {
        visibility: hidden; opacity: 0; position: fixed;
        width: 300px; max-height: 308px; overflow-y: auto;
        display: flex; flex-direction: column;
        background-color: var(--color-background); color: var(--color-text);
        border: 1px solid var(--color-border); border-radius: 6px;
        z-index: 999; transition: opacity 0.2s; box-shadow: 0 4px 6px rgba(0,0,0,0.3);
      }
      .tooltip.show { visibility: visible; opacity: 1; }
      .tooltip-header {
        position: sticky; top: 0; z-index: 1;
        background-color: var(--color-background);
        padding: 4px 8px; text-align: right;
        border-bottom: 1px solid var(--color-border);
      }
      .tooltip-header button {
        background-color: var(--color-interactive-background); color: var(--color-text);
        border: 1px solid var(--color-border); border-radius: 4px;
        padding: 2px 8px; font-size: 0.8em; cursor: pointer;
      }
      .tooltip-header button:hover { background-color: var(--color-interactive-background-hover); }
      .tooltip-content { padding: 8px; font-size: 0.9em; }
      .tooltip-content ul { list-style: none; padding: 0; margin: 0; }
      .tooltip-content li {
        display: flex; justify-content: space-between; align-items: center;
        padding: 5px 4px; border-bottom: 1px solid var(--color-border-subtle); border-radius: 3px;
      }
      .tooltip-content li:last-child { border-bottom: none; }
      .tooltip-content li:hover { background-color: var(--color-background-hover); }
      .tooltip-content a { color: inherit; text-decoration: none; }
      .tooltip-content a:hover { text-decoration: underline; }
      .tooltip-content .full-width-link { display: flex; justify-content: space-between; align-items: center; width: 100%; }
      .tooltip-content .item-name, .tooltip-content .item-link { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .tooltip-content .context-text, .tooltip-content .context-link {
        font-size: 0.9em; opacity: 0.7; margin-left: 10px;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex-shrink: 0;
      }
    </style>

    <img src=x style="display:none" onerror="
      const CACHE_DURATION_MS = {{ .Options.IntOr `list_cache_minutes` 15 }} * 60 * 1000;
      window.hoverIsEnabled = {{ .Options.BoolOr `hover_enabled` true }};
      window.navidromeConfig = { baseUrl: null };
      window.tooltipState = { hideTimeout: null, controller: null, currentData: [], currentType: null, sortDir: 'asc' };
      window.listCache = { artists: null, albums: null, songs: null };

      fetch('${secret:SUBSONIC_PROXY_URL}/config').then(res => res.json()).then(data => { 
        window.navidromeConfig.baseUrl = data.baseUrl;
        if (data.baseUrl) {
          document.getElementById('artists-link').href = `${data.baseUrl}/app/#/artist`;
          document.getElementById('albums-link').href = `${data.baseUrl}/app/#/album/all`;
          document.getElementById('songs-link').href = `${data.baseUrl}/app/#/song`;
        }
      });

      window.renderList = function(data, type) {
        const tooltipContent = document.getElementById('tooltip-content');
        let listHtml = '<ul>';
        if (data && data.length > 0) {
          const baseUrl = window.navidromeConfig.baseUrl;
          data.forEach(item => {
            if (type === 'albums') {
              const albumLink = `<a class='item-link' href='${baseUrl}/#/album/${item.id}/show' target='_blank'>${item.name || 'Unknown'}</a>`;
              const artistLink = item.artistId ? `<a class='context-link' href='${baseUrl}/#/artist/${item.artistId}/show' target='_blank'>${item.artistName || ''}</a>` : '';
              listHtml += `<li>${albumLink}${artistLink}</li>`;
            } else {
              let href = '#';
              if (type === 'artists') { href = `${baseUrl}/#/artist/${item.id}/show`; }
              else if (type === 'songs') { href = `${baseUrl}/#/album/${item.albumId}/show`; }
              const contextHtml = item.context ? `<span class='context-text'>${item.context}</span>` : '';
              listHtml += `<li><a href='${href}' target='_blank' class='full-width-link'><span class='item-name'>${item.name || 'Unknown'}</span>${contextHtml}</a></li>`;
            }
          });
        } else { listHtml += '<li>No items found.</li>'; }
        tooltipContent.innerHTML = listHtml + '</ul>';
      };

      window.sortTooltip = function() {
        const data = window.tooltipState.currentData;
        const button = document.getElementById('sort-button');
        const newDir = window.tooltipState.sortDir === 'asc' ? 'desc' : 'asc';
        data.sort((a, b) => {
          const nameA = String(a.name || '').toLowerCase();
          const nameB = String(b.name || '').toLowerCase();
          if (newDir === 'desc') { return nameB.localeCompare(nameA); }
          return nameA.localeCompare(nameB);
        });
        window.tooltipState.sortDir = newDir;
        button.textContent = newDir === 'asc' ? 'Sort Z-A' : 'Sort A-Z';
        window.renderList(data, window.tooltipState.currentType);
      };

      window.handleData = function(data, type) {
        data.sort((a, b) => String(a.name || '').toLowerCase().localeCompare(String(b.name || '').toLowerCase()));
        window.tooltipState.currentData = data;
        window.tooltipState.currentType = type;
        window.tooltipState.sortDir = 'asc';
        document.getElementById('sort-button').textContent = 'Sort Z-A';
        window.renderList(data, type);
      };

      window.showTooltip = function(type, element) {
        if (!window.hoverIsEnabled) return;
        if (!window.navidromeConfig.baseUrl) return;
        const tooltip = document.getElementById('lazy-tooltip');
        const tooltipContent = document.getElementById('tooltip-content');
        clearTimeout(window.tooltipState.hideTimeout);
        if (window.tooltipState.controller) window.tooltipState.controller.abort();

        const rect = element.getBoundingClientRect(), tooltipWidth = 300, tooltipHeight = 308, margin = 8;
        let top = rect.bottom + margin, left = rect.left + (rect.width / 2) - (tooltipWidth / 2);
        if (top + tooltipHeight > window.innerHeight) { top = rect.top - tooltipHeight - margin; }
        if (left < margin) { left = margin; } else if (left + tooltipWidth > window.innerWidth - margin) { left = window.innerWidth - tooltipWidth - margin; }
        tooltip.style.top = top + 'px';
        tooltip.style.left = left + 'px';
        tooltip.classList.add('show');

        const now = new Date().getTime();
        const cachedItem = window.listCache[type];
        if (cachedItem && (now - cachedItem.timestamp < CACHE_DURATION_MS)) {
          tooltipContent.innerHTML = '';
          window.handleData(cachedItem.data, type);
          return;
        }

        tooltipContent.innerHTML = 'Loading...';
        window.tooltipState.controller = new AbortController();
        const signal = window.tooltipState.controller.signal;

        fetch('${secret:SUBSONIC_PROXY_URL}/' + type, { signal })
          .then(response => response.ok ? response.json() : Promise.reject('API Error'))
          .then(data => {
            window.listCache[type] = { data: data, timestamp: new Date().getTime() };
            window.handleData(data, type);
          })
          .catch(error => { if (error.name !== 'AbortError') tooltipContent.innerHTML = 'Error loading data.'; });
      };

      window.hideTooltip = function() {
        window.tooltipState.hideTimeout = setTimeout(() => {
          if (window.tooltipState.controller) window.tooltipState.controller.abort();
          document.getElementById('lazy-tooltip').classList.remove('show');
        }, 300);
      };
    ">

    <div class="flex justify-around text-center">
      <a id="artists-link" href="#" target="_blank" class="stat-link">
        <div class="stat-block" onmouseenter="showTooltip('artists', this.parentElement)" onmouseleave="hideTooltip()">
          <div class="color-highlight size-h3">{{ .JSON.Int `artistCount` | formatNumber }}</div>
          <div class="size-h6">ARTISTS</div>
        </div>
      </a>
      <a id="albums-link" href="#" target="_blank" class="stat-link">
        <div class="stat-block" onmouseenter="showTooltip('albums', this.parentElement)" onmouseleave="hideTooltip()">
          <div class="color-highlight size-h3">{{ .JSON.Int `albumCount` | formatNumber }}</div>
          <div class="size-h6">ALBUMS</div>
        </div>
      </a>
      <a id="songs-link" href="#" target="_blank" class="stat-link">
        <div class="stat-block" onmouseenter="showTooltip('songs', this.parentElement)" onmouseleave="hideTooltip()">
          <div class="color-highlight size-h3">{{ .JSON.Int `songCount` | formatNumber }}</div>
          <div class="size-h6">SONGS</div>
        </div>
      </a>
    </div>

    <div id="lazy-tooltip" class="tooltip" onmouseenter="clearTimeout(window.tooltipState.hideTimeout)" onmouseleave="hideTooltip()">
      <div class="tooltip-header">
        <button id="sort-button" onclick="sortTooltip()">Sort Z-A</button>
      </div>
      <div id="tooltip-content" class="tooltip-content"></div>
    </div>
```
