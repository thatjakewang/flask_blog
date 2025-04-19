document.addEventListener("DOMContentLoaded", function () {
  //獲取當前頁面的 URL 路徑
  var path = window.location.pathname;
  var menuItems = document.querySelectorAll(".dashboard_menu ul li");

  menuItems.forEach(function (item) {
    item.classList.remove("active");
  });

  menuItems.forEach(function (item) {
    //在每個 <li> 中查找 <a> 元素
    var link = item.querySelector("a");
    // if link 存在 TrueTrue
    if (link) {
      // 獲取 <a> 元素的 href 屬性值 = 連結路徑. e.g. /dashboard
      var href = link.getAttribute("href");

      if (
        href === path ||
        (path.includes("/posts") && href.includes("/posts")) ||
        (path === "/dashboard/" &&
          href.includes("/dashboard") &&
          href.length === 11)
      ) {
        item.classList.add("active");
      }
    }
  });
});
