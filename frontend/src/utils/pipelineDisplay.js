export function formatGitUrl(url) {
  if (!url) return"";
  return url.replace("https://","").replace("http://","").replace(".git","");
}

export function formatDateTime(isoString) {
  if (!isoString) return"";
  const date = new Date(isoString);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2,"0");
  const day = String(date.getDate()).padStart(2,"0");
  const hours = String(date.getHours()).padStart(2,"0");
  const minutes = String(date.getMinutes()).padStart(2,"0");
  const seconds = String(date.getSeconds()).padStart(2,"0");
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}

export function isLastBuildRunning(pipeline) {
  return (
    pipeline?.last_build &&
    (pipeline.last_build.status ==="running" ||
      pipeline.last_build.status ==="pending")
  );
}
