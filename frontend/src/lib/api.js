const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").trim();

export async function getOptions() {
  return requestJson("/options");
}

export async function generatePreview(payload) {
  return requestJson("/generate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
}

export async function generatePreviewWithProgress(payload, onProgress) {
  const status = await runJob(
    () =>
      requestJson("/jobs/preview", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      }),
    onProgress,
  );

  return status.result;
}

export async function downloadPpt(payload) {
  const response = await fetch(resolveApiUrl("/generate-ppt"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const payloadBody = await safeReadJson(response);
    throw new Error(payloadBody?.detail ?? "The PowerPoint file could not be created.");
  }

  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition");
  const matches = disposition?.match(/filename=\"?([^\"]+)\"?/i);
  const filename = matches?.[1] ?? "automation-output.pptx";
  return { blob, filename };
}

export async function downloadPptWithProgress(payload, onProgress) {
  const status = await runJob(
    () =>
      requestJson("/jobs/ppt", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      }),
    onProgress,
  );

  onProgress?.({
    ...status,
    progress: 100,
    message: "Preparing your download...",
  });

  return downloadJobFile(status.job_id);
}

export async function downloadVersePpt(payload, styleFile) {
  const formData = new FormData();
  formData.append("payload", JSON.stringify(payload));
  if (styleFile) {
    formData.append("style_file", styleFile);
  }

  const response = await fetch(resolveApiUrl("/verses/generate-ppt"), {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const payloadBody = await safeReadJson(response);
    throw new Error(payloadBody?.detail ?? "The verse PowerPoint file could not be created.");
  }

  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition");
  const matches = disposition?.match(/filename=\"?([^\"]+)\"?/i);
  const filename = matches?.[1] ?? "verses-output.pptx";
  return { blob, filename };
}

export async function downloadVersePptWithProgress(payload, styleFile, onProgress) {
  const status = await runJob(
    async () => {
      const formData = new FormData();
      formData.append("payload", JSON.stringify(payload));
      if (styleFile) {
        formData.append("style_file", styleFile);
      }

      return requestJson("/jobs/verses-ppt", {
        method: "POST",
        body: formData,
      });
    },
    onProgress,
  );

  onProgress?.({
    ...status,
    progress: 100,
    message: "Preparing your download...",
  });

  return downloadJobFile(status.job_id);
}

export function saveBlobFile(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  window.URL.revokeObjectURL(url);
}

async function requestJson(path, init) {
  const response = await fetch(resolveApiUrl(path), init);
  const payload = await safeReadJson(response);

  if (!response.ok) {
    throw new Error(payload?.detail ?? "Request failed.");
  }

  return payload;
}

async function runJob(startJob, onProgress) {
  let status = await startJob();
  onProgress?.(status);

  while (status.status === "queued" || status.status === "running") {
    await sleep(320);
    status = await requestJson(`/jobs/${status.job_id}`);
    onProgress?.(status);
  }

  if (status.status === "failed") {
    throw new Error(status.error ?? status.message ?? "Request failed.");
  }

  return status;
}

async function downloadJobFile(jobId) {
  const response = await fetch(resolveApiUrl(`/jobs/${jobId}/download`));

  if (!response.ok) {
    const payloadBody = await safeReadJson(response);
    throw new Error(payloadBody?.detail ?? "The PowerPoint file could not be created.");
  }

  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition");
  const matches = disposition?.match(/filename=\"?([^\"]+)\"?/i);
  const filename = matches?.[1] ?? "automation-output.pptx";
  return { blob, filename };
}

async function safeReadJson(response) {
  const text = await response.text();
  return text ? JSON.parse(text) : null;
}

function sleep(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function resolveApiUrl(path) {
  return API_BASE ? `${API_BASE}${path}` : path;
}
