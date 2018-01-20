Title: 通过 Preconnect 加速网站资源的加载
Date: 2018-01-20 00:00
Modified: 2018-01-20 00:00
Slug: verses/5bfc8b7a-ab1e-46aa-8b71-bfb6ad084f1c
Category: verses
Authors: Ju Lin

[查看原文](https://www.viget.com/articles/make-your-site-faster-with-preconnect-hints/)

正常加载资源需要经历 DNS 查找，TCP 握手，TLS 协商等环节才能开始下载数据，我们可以引入一个 preconnect 的提示让浏览器预先连上网站，从而加速资源的获取，提高网站的性能。具体做法在 link 标签里面填写 rel="preconnect", href="https://the-website-you-want-to-connect" 即可。在本文的示例中可以看到在设定了 googlefont 的预先连接后，资源加载时间减半。需要注意的一点是，`crossorigin` 标识在这个场景下是必须的，因为字体加载是异步的操作。另外注意的一点是，这个标识只是给浏览器的 hint，具体能不能生效，得看具体的浏览器，一般来说，chrome 会没啥问题。

