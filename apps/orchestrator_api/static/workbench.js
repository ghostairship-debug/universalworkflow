(function () {
  const stream = document.getElementById("chat-stream");
  const form = document.getElementById("chat-form");
  const submit = document.getElementById("chat-submit");
  const statusFeed = document.getElementById("workflow-status-feed");
  const sessionStatus = document.getElementById("chat-session-status");
  const activeRun = document.getElementById("chat-active-run");
  const llmStatus = document.getElementById("chat-llm-status");
  const graphNode = document.getElementById("chat-graph-node");
  if (!stream || !window.EventSource) {
    return;
  }

  const baseStreamUrl = stream.dataset.streamUrl || "";
  const seenEvents = new Set();
  let lastEventId = "";
  let reconnectTimer = null;

  const appendStatus = function (text) {
    if (!statusFeed) return;
    if (statusFeed.dataset.empty !== "false") {
      statusFeed.textContent = "";
      statusFeed.dataset.empty = "false";
    }
    const item = document.createElement("div");
    item.className = "stream-event";
    item.textContent = text;
    statusFeed.appendChild(item);
  };

  const appendMeta = function (item, role, actionType) {
    const meta = document.createElement("div");
    meta.className = "chat-meta";
    const rolePill = document.createElement("span");
    rolePill.className = "pill pill-info";
    rolePill.textContent = role || "assistant";
    const action = document.createElement("span");
    action.textContent = actionType || "message";
    meta.appendChild(rolePill);
    meta.appendChild(action);
    const content = document.createElement("div");
    content.className = "chat-content";
    item.appendChild(meta);
    item.appendChild(content);
    return content;
  };

  const appendConfirmationCard = function (item, message, confirmation) {
    const card = document.createElement("div");
    card.className = "confirmation-card";
    const title = document.createElement("strong");
    title.textContent = "Confirmation required";
    const detail = document.createElement("p");
    detail.className = "muted";
    detail.textContent = "action=" + (confirmation.action_type || "-") + " run=" + (confirmation.run_id || "-");
    const actions = document.createElement("div");
    actions.className = "actions actions-compact";
    const button = document.createElement("button");
    button.className = "warn chat-confirm-button";
    button.type = "button";
    button.dataset.chatConfirmAction = message.message_id;
    button.textContent = "Confirm";
    actions.appendChild(button);
    card.appendChild(title);
    card.appendChild(detail);
    card.appendChild(actions);
    item.appendChild(card);
  };

  const appendChat = function (message) {
    if (!message || !message.message_id) {
      return;
    }
    const existing = stream.querySelector('[data-message-id="' + message.message_id + '"]');
    if (existing) {
      if (existing.dataset.streaming === "true") {
        const content = existing.querySelector(".chat-content");
        if (content) content.textContent = message.content || "";
        delete existing.dataset.streaming;
      }
      return;
    }
    const item = document.createElement("div");
    item.className = "chat-message chat-" + (message.role || "assistant");
    item.dataset.messageId = message.message_id;
    appendMeta(item, message.role || "assistant", message.action_type || "message").textContent = message.content || "";
    const confirmation = message.payload_json && message.payload_json.confirmation;
    if (message.message_type === "confirmation_required" && message.status === "pending_confirmation" && confirmation) {
      appendConfirmationCard(item, message, confirmation);
    }
    stream.appendChild(item);
    stream.scrollTop = stream.scrollHeight;
  };

  const appendAssistantDelta = function (payload) {
    const messageId = payload && payload.message_id;
    if (!messageId) return;
    let item = stream.querySelector('[data-message-id="' + messageId + '"]');
    if (!item) {
      item = document.createElement("div");
      item.className = "chat-message chat-assistant";
      item.dataset.messageId = messageId;
      item.dataset.streaming = "true";
      appendMeta(item, "assistant", "stream");
      stream.appendChild(item);
    }
    if (item.dataset.streaming !== "true") {
      return;
    }
    item.querySelector(".chat-content").textContent += payload.delta || "";
    stream.scrollTop = stream.scrollHeight;
  };

  const handleEvent = function (label, payload, eventId) {
    if (eventId && eventId.indexOf("chatevt_") === 0) {
      lastEventId = eventId;
    }
    const eventKey = eventId || (label + ":" + JSON.stringify(payload || {}));
    if (seenEvents.has(eventKey)) {
      return;
    }
    seenEvents.add(eventKey);
    if (label === "user_message" || label === "assistant_final" || label === "confirmation_required" || label === "confirmation_result" || label === "error") {
      appendChat(payload);
      return;
    }
    if (label === "assistant_delta") {
      appendAssistantDelta(payload);
      return;
    }
    if (label === "graph_update") {
      if (graphNode) graphNode.textContent = payload.graph_node || payload.path?.slice(-1)[0] || "updated";
      appendStatus("graph_update: " + (payload.graph_node || "updated"));
      return;
    }
    if (label === "status_patch") {
      const session = payload.session || {};
      if (sessionStatus && session.status) sessionStatus.textContent = session.status;
      if (activeRun) activeRun.textContent = payload.active_run_id || session.active_run_id || "-";
      if (llmStatus && payload.llm) {
        const baseLlm = payload.llm.configured ? (payload.llm.provider + " / " + payload.llm.model) : "LLM degraded";
        const modelSelection = payload.model_selection || {};
        const selectedModel = modelSelection.selected_model || "";
        const selectionSource = modelSelection.model_selection_source || "";
        llmStatus.textContent = selectedModel ? (baseLlm + " | " + selectedModel + (selectionSource ? " / " + selectionSource : "")) : baseLlm;
      }
      appendStatus("status_patch: updated");
      return;
    }
    if (label === "run_update" || label === "timeline_event" || label === "test_evidence" || label === "pr_ready_summary" || label === "review_required") {
      appendStatus(label + ": " + (payload.headline || payload.event_type || payload.summary || payload.run_id || "updated"));
    }
  };

  const parsePayload = function (event) {
    try {
      return JSON.parse(event.data);
    } catch (_error) {
      return { content: event.data || "event parse failed" };
    }
  };

  stream.addEventListener("click", function (event) {
    const target = event.target;
    const button = target && target.closest ? target.closest("[data-chat-confirm-action]") : null;
    if (!button) return;
    const actionId = button.getAttribute("data-chat-confirm-action");
    if (!actionId) return;
    button.disabled = true;
    fetch("/interaction/chat/actions/" + encodeURIComponent(actionId) + "/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rationale: "confirmed from workbench chat" })
    })
      .then(function (response) {
        return response.json().then(function (payload) {
          if (!response.ok) {
            const message = payload && payload.error && payload.error.message
              ? payload.error.message
              : "HTTP " + response.status;
            throw new Error(message);
          }
          return payload;
        });
      })
      .then(function (payload) {
        (payload.chat_stream_events || []).forEach(function (item) {
          handleEvent(item.event_type, item.payload_json, item.event_id);
        });
      })
      .catch(function (error) {
        appendChat({ message_id: "error_" + Date.now(), role: "assistant", action_type: "error", content: "confirm failed: " + error });
        button.disabled = false;
      });
  });

  const connectStream = function () {
    const url = lastEventId
      ? baseStreamUrl + "?after_event_id=" + encodeURIComponent(lastEventId)
      : baseStreamUrl;
    const source = new EventSource(url);
    let heartbeatReceived = false;
    ["user_message", "assistant_delta", "assistant_final", "tool_action_proposed", "confirmation_required", "confirmation_result", "graph_update", "run_update", "status_patch", "timeline_event", "review_required", "test_evidence", "pr_ready_summary", "error"].forEach(function (name) {
      source.addEventListener(name, function (event) {
        handleEvent(name, parsePayload(event), event.lastEventId);
      });
    });
    source.addEventListener("heartbeat", function () {
      heartbeatReceived = true;
      source.close();
      if (!reconnectTimer) {
        reconnectTimer = window.setTimeout(function () {
          reconnectTimer = null;
          connectStream();
        }, 3000);
      }
    });
    source.addEventListener("error", function () {
      if (heartbeatReceived) {
        source.close();
        return;
      }
      appendStatus("event stream disconnected; retrying");
      source.close();
      if (!reconnectTimer) {
        reconnectTimer = window.setTimeout(function () {
          reconnectTimer = null;
          connectStream();
        }, 5000);
      }
    });
  };

  if (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      const formData = new FormData(form);
      const message = (formData.get("message") || "").toString().trim();
      if (!message) return;
      if (submit) submit.disabled = true;
      fetch("/interaction/chat/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: formData.get("session_id") || null,
          content: message,
          mode: "llm_assisted",
          client_message_id: "client_" + Date.now()
        })
      })
        .then(function (response) {
          return response.json().then(function (payload) {
            if (!response.ok) {
              const message = payload && payload.error && payload.error.message
                ? payload.error.message
                : "HTTP " + response.status;
              throw new Error(message);
            }
            return payload;
          });
        })
        .then(function (payload) {
          form.querySelector("textarea").value = "";
          const nextSessionId = payload && payload.session && payload.session.session_id;
          const currentSessionId = (formData.get("session_id") || "").toString();
          if (nextSessionId && currentSessionId && nextSessionId !== currentSessionId) {
            window.location.href = "/ui/workbench?session_id=" + encodeURIComponent(nextSessionId);
            return;
          }
          (payload.chat_stream_events || []).forEach(function (item) {
            handleEvent(item.event_type, item.payload_json, item.event_id);
          });
        })
        .catch(function (error) {
          appendChat({ message_id: "error_" + Date.now(), role: "assistant", action_type: "error", content: "send failed: " + error });
        })
        .finally(function () {
          if (submit) submit.disabled = false;
          connectStream();
        });
    });
  }
  connectStream();
})();
