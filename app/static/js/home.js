document.addEventListener("DOMContentLoaded", () => {
  const nameSelect = document.getElementById("name");
  const passwordWrap = document.getElementById("password-wrap");
  const passwordInput = document.getElementById("access_password");

  if (!nameSelect || !passwordWrap) return;

  const syncPasswordVisibility = () => {
    const hasName = Boolean(nameSelect.value);
    passwordWrap.classList.toggle("hidden", !hasName);
    if (passwordInput) {
      passwordInput.required = hasName;
      if (!hasName) passwordInput.value = "";
    }
  };

  nameSelect.addEventListener("change", syncPasswordVisibility);
  syncPasswordVisibility();
});
