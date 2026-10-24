var g_helpers = null;

function newPageOpen(e) {
	if (e.ctrlKey && e.shiftKey) {
        window.open($(e.currentTarget).data('href'), '_blank');
	}
    return false;
}

function copyToClipboard(element) {
	var str = element.attr('href');
    element.append("<textarea id=\"tmp_copy\" readonly=\"readonly\">" + str + "</textarea>");
    var copyElement = $("#tmp_copy")[0];
    copyElement.select();

    var range = document.createRange();
    range.selectNodeContents(copyElement);
    var sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
    copyElement.setSelectionRange(0, 999999);
	var isCopy = document.execCommand("copy");
	$("#tmp_copy").remove();

	if (isCopy) {
		alert('URLのコピーが完了しました。\n'+str);
	} else {
		alert('このブラウザでは対応していません。');
	}
}

$(function () {
	var $popup = $('#cardlist a[data-href]').add('.modal_popup');
	//$popup.addClass('ajax_pop');

	if($('.modal-window').length){
		$('<img src="/common/img/loading.gif" class="loading" width="80">').prependTo('.modal-window');
		var ajax = {
			load: function (options) {
				var ajaxOptions = $.extend({
					dataType: "html",
					type: "GET",
					cache: true,
					beforeSend: function () {},
					success: function (res) { console.log("success", res);},
					error: function (res) { console.error("error loading", res);},
					complete: function (jxhr) { console.log("complete", jxhr);}
				}, options);
				if (!ajaxOptions.url) {
					console.error("URL not defined"); return;
				}
				$.ajax(ajaxOptions);
			}
		};
		var $window = $(window),
			$html   = $('html'),
			$body   = $('body'),
			ctlClass = "dmv2",
			helpers = {
				modalWindow: function ($elms, type) {
					var $button_modal = $(".btn-open-modal"),
						$modal_window = $(".modal-window"),
						$modal_close = $(".button-close"),
						page_scroll,
						onAjaxLoaded = function (res, detail_url) {
							var $html = $(res),
								$modal = $(".modal-window.card"),
								$modal_card = $modal.find(".modal-card"),
								$modal_template = $modal.find(".card-template"),
								$info_template = $modal.find(".card_info-template"),
								$grid = $modal.find(".grid"),
								$cards = $html.find("table"),
								$card_amount = $cards.length,
								$illust_amount = 1,
								assets = {},
								$prod_slug = $html.find("#product_slug"),
								$qa_url = $html.find("#qa_url"),
								$products = $html.find(".productCard"),
								$card_itself;
							$modal.find(".card-itself, .card_info").remove();
							for (var k = 0; k <= $card_amount - 1; k++) {
								//$modal_template.clone().addClass("card-itself").removeClass("card-template hide").appendTo(".modal-card");
								$modal_template.clone().addClass("card-itself").removeClass("card-template hide").prependTo(".modal-card");
								$card_itself = $modal.find(".card-itself");
							}

							if (type !== undefined && type === "product") {
							// カードをテンプレートから枚数分クローン

								for (var j = 0; j <= $card_amount - 1; j++) {
									//page-dettail.phpから特定の要素を探して要素内の内容を配列に格納
									assets = {
										title: $html.find(".cardname").eq(j).html(),
										annotation: $html.find(".annotation td").eq(j).html(),
										image: $html.find(".cardimg img").eq(j).attr("src"),
										pack: $html.find(".card_package").eq(j).html(),
										type: $html.find(".typetxt").eq(j).html(),
										rarelity: $html.find(".raretxt").eq(j).html(),
										cost: $html.find(".costtxt").eq(j).html(),
										race: $html.find(".racetxt").eq(j).html(),
										illust: $html.find(".illusttxt").eq(j).html(),
										civil: $html.find(".civtxt").eq(j).html(),
										power: $html.find(".powertxt").eq(j).html(),
										mana: $html.find(".manatxt").eq(j).html(),
										skill: $html.find(".abilitytxt").eq(j).html(),
										flavor: $html.find(".flavortxt").eq(j).html()
									};
									// modal-window-card.phpに内容を出力
									$card_itself.eq(j).find(".card-name").html(assets.title);
									$card_itself.eq(j).find(".annotation").html(assets.annotation);
									if(!assets.annotation) $card_itself.eq(j).find(".annotation").remove();
									$card_itself.eq(j).find("img").attr("src", assets.image);
									$card_itself.eq(j).find(".card_package").html(assets.pack);
									$card_itself.eq(j).find(".type").html(assets.type);
									$card_itself.eq(j).find(".rarelity").html(assets.rarelity);
									$card_itself.eq(j).find(".cost").html(assets.cost);
									$card_itself.eq(j).find(".race").html(assets.race);
									$card_itself.eq(j).find(".illust").html(assets.illust);
									if(j>0) $card_itself.eq(j).find(".illust").parents('table').remove();
									$card_itself.eq(j).find(".civil").html(assets.civil);
									$card_itself.eq(j).find(".power").html(assets.power);
									$card_itself.eq(j).find(".mana").html(assets.mana);
									$card_itself.eq(j).find(".skills ul").html(assets.skill);
									$card_itself.eq(j).find(".flavor").html(assets.flavor);
								}

								// リンクエリアを追加
								var $addInfo = $info_template.clone().addClass("card_info").removeClass("card_info-template hide");
								if ($prod_slug[0]) {
									var prod_url = "/product/" + $prod_slug.val() + "/";
									$addInfo.find(".bnr a").eq(0).attr("href", prod_url);
								}
								if ($qa_url[0]) {
									$addInfo.find(".bnr a").eq(1).attr("href", $qa_url.val());
								} else {
									$addInfo.find(".bnr a").eq(1).remove();
								}
								$addInfo.find(".sns a").each(function() {
									var $this = $(this);
									var share = $this.attr("href");
									share = share.replace(/#url#/g, detail_url);
									share = share.replace(/ツイート情報/g, assets.title);
									share = share.replace('<span class="packname">', '');
									share = share.replace('</span>', '');
									$this.attr("href", share);
								});
								if (!$prod_slug[0]) {
									$addInfo.find(".bnr a").eq(0).remove();
								}
								//$addInfo.appendTo(".modal-card");
								$addInfo.appendTo(".card-itself .row .grid");

								// 同名カードが含まれる商品名を表示
								$(".productCard").remove();
								$(".card-itself").eq(-1).after($products);

							} else if (type !== undefined && type === "slug-product") {
								assets = {
									title:      $html.find(".prod_title").text(),
									image:      $html.find(".prod_img_png"),
									price:      $html.find(".price").text(),
									sales_date: $html.find(".sales_date").text(),
									text:       $html.find(".info_text span").html()
								};
								$card_itself.eq(0).find(".card-name").html(assets.title);
								$card_itself.eq(0).find(".product_image").html(assets.image);
								$card_itself.eq(0).find(".price").html(assets.price);
								$card_itself.eq(0).find(".sales_date").html(assets.sales_date);
								$card_itself.eq(0).find(".text").html(assets.text);
							}
							
							$modal_window.addClass("modal-show");
							$modal_card.scrollTop(0);
						},
						onCloseModal = function () {
							$modal_window.removeClass("fadeIn");
							setTimeout(function(){
								$(".card-itself").remove(); // Kill all zombies
								$(".productCard").remove();
								$modal_window.removeClass("modal-show");
								$window.scrollTop(page_scroll);
							},500);
						};
					$('.ajax_pop').off('click').on('click',function(e){
						page_scroll = $window.scrollTop();
						e.preventDefault();
						if ( !(e.ctrlKey && e.shiftKey) ) {
							var url = $(this).attr('data-href') || $(this).attr('href');

							$modal_window.removeClass("modal-show").addClass('fadeIn');
							//setTimeout(function(){
								ajax.load({
									url: url,
									success: function(responseText) {
										onAjaxLoaded(responseText, url);
									}
								});
							//},500);
						}
					});
					$modal_close.on("click", onCloseModal);
				}
			};
		g_helpers = helpers;
		if ($(".modal-window.card.product")[0]) {
			var $cardlinks = $(".ajax_pop");
			if ($cardlinks.length) {
				helpers.modalWindow($cardlinks, "slug-product");
			}
		} else {
			var $cardlinks = $(".ajax_pop");
			if ($cardlinks.length) {
				helpers.modalWindow($cardlinks, "product");
			}
		}

		$(".modal-card").on("click", ".detailBtn02", function() {
			$(this).toggleClass("current2");
			$(".productCardList").slideToggle("fast");
		});

		$(".modal-card").on("click", ".share_copy", function(event) {
			event.preventDefault();
			copyToClipboard($(this));
		});
	}

	$(".cardDetail").on("click", ".share_copy", function(event) {
		event.preventDefault();
		copyToClipboard($(this));
	});

});