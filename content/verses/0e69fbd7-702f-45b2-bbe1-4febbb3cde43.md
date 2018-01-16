Title: 哪个 Web 框架最快？
Date: 2018-01-16 00:00
Modified: 2018-01-16 00:00
Slug: verses/0e69fbd7-702f-45b2-bbe1-4febbb3cde43
Category: verses
Authors: Ju Lin

[查看原文](https://github.com/tbrand/which_is_the_fastest)

给出这个命题，能给出一个不错的解答其实需要大量的涉猎，作者给出的答案是 router_cr(crystal) 最快，Python 框架中最快的是 Japronto，语言上 crystal > rust > python > go, 但也得看具体框架的性能。测量的基准是 8 核 CPU 的 CPU，遵循的 Rule 是无逻辑，就是做 route 解析和响应生成。