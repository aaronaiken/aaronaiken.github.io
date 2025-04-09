---
layout: status
title: status updates
author: aaron
---

{% assign sorted_updates = site.status_updates | sort: 'date' | reverse %}
<ul>
  {% for post in sorted_updates %}
	<li>{{ post.content | markdownify | strip_html | truncate: 140 }} - <a href="{{ post.url }}" target="_blank">{{ post.date | date: "%Y-%m-%d %H:%M:%S %z" }}</a></li>
  {% endfor %}
</ul>