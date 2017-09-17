# Tech Shack

## 简介

Tech Shack 是一个博客，聚合了 @soasme 个人技术阅读和心得体会。
既定目标是每天阅读篇数不定的技术文章，做一些摘要，可能有衍生思考。

* [查看最近的阅读](https://techshack.soasme.com)
* [查看所有的阅读](https://techshack.soasme.com/archive.html)


## 底层技术

Show me the code: [soasme/techshack.io](https://github.com/soasme/techshack.io)

* 本地使用 ssh 部署 Python Slackbot script 到服务器。
* 服务器使用 Nginx 设定静态目录的 root path。
* Slackbot 发出一些命令完成数据录入，网站编译，和 SNS 分享。

## 工作流

每天要做的事情写成伪代码，可以是这个样子：

```bash
for src in "feedly manpage pythondocs onlinebook etc";
do
    getpocket < $src
done

getpocket | head -n 5 | read | slackbot --publish
```

* 看到比较晚，还没有到达五篇，一天也就不读了。
* 看得超过了五篇，觉得酣畅淋漓，也就多读些。

## 内容

* 翻译大致内容。提升自己的英语，也帮助别人不会因为语言障碍错过好文章。也鼓励大家看原文，一来会有与我不同的想法或许可以讨论，二来不致被我带歪思路。
* 把一些正程序员三观的观点写下来。
* 记录手册文档中觉得对工作会有帮助的地方。
* 学习一些奇淫巧技。

## 难点

只有一个：坚持做下去。

工作五年，还没有一个能持续运行下去的项目。

想了一下：

* 既然自己的博客关于工作，学习，生活能写十年，那博客中技术阅读那部分分拆出来有很大概率也能坚持做下去。
* 这些年技术阅读记录的比较散，博客中记得多是整理好的，那些看过一遍的好文章可能就没个索引，比较可惜。

## 开销

| Item       | Service                       | Price   |
|------------|-------------------------------|---------|
| Host       | Linode 1GB                    | $5/mo   |
| Domain     | Share with personal id domain | $0/mo   |
| CDN        | Rawgit                        | $0/mo   |
| SSL        | Letsencrypt                   | $0/mo   |
| Automation | Slack                         | $0/mo   |
