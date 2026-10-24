var scroll_pos = "";
// 非同期処理周り
$(function() {
	search_initialize('initial');
	
	// URLにデータがあったら再検索
	var urlParam = decodeURI(location.search.substring(1));
	var param_json = null;
	if(urlParam != ""){
		var param = urlParam.split('=')[1];
		param_json = JSON.parse(param);
		research(param_json);
	}
	
	let $form = $("form#search_cond,#sort-area");

	$form.on("submit", function() {
		// 非同期でページ取得して流し込み
		let target = $form.attr("action");
		let data = {};
		let history_state = {}; //検索履歴用
		$form.find("input[type=text],input[type=number],input[type=checkbox]:checked,input[type=hidden]").each(function() {
			let $this = $(this);
			let name = $this.attr("name");
			let val = $this.val();
			if (val != "") {
				if (name.indexOf('[]') != -1) {
					name = name.replace('[]','');
					if (!data[name]){
						data[name] = [];
						history_state[name] = [];
					}
					data[name].push(val);
					history_state[name].push(val);
				} else {
					data[name] = val;
					history_state[name] = val;
				}
			}

		});
		$form.find("select").each(function() {
			let $this = $(this);
			let val = $this.find("option:selected").val();
			if (val != "") {
				data[$this.attr("name")] = val;
				history_state[$this.attr("name")] = val;
			}
		});
		//pushState(履歴保存)
		var date = new Date();
		var history_state_str = JSON.stringify(history_state);
		var url = encodeURI('?v='+history_state_str);
		history.pushState(history_state,"",url);
		doAjax("/card/", data, ".sectionFormat05");
		//カードリストまでスクロール
		var list_pos = $('#cardlist_wrap').offset().top;
		$('html, body').animate({scrollTop:list_pos});
		return false;
	});
	initPage();
	
	//文明(含める)
	$('input:checkbox[name="culture[]"]').not('#culture06').change(function(){
		search_cond_add();
	});

	//文明(単色・多色)チェック切り替え時
	$('input:checkbox[name="culture_cond[]"]').change(function(){
		var index = $('input:checkbox[name="culture_cond[]"]').index(this);
		var off_count = 0;
		$('input:checkbox[name="culture_cond[]"]').each((index,element)=>{
			if(!$(element).prop('checked'))
				off_count++;
		});
		//どれもチェックされていなければ再チェック
		if(off_count === $('input:checkbox[name="culture_cond[]"]').length)
			$('input:checkbox[name="culture_cond[]"]').eq(index).prop('checked',true);
		
		search_cond_add();
	});
	
	//文明クリックアニメーション
	$('input:checkbox[name="culture_cond[]"],input:checkbox[name="culture[]"],input:checkbox[name="culture_exclude[]"]').on('click',function(){
		//クリックアニメーション
		var id = $(this).attr("id");
		$('label[for="'+id+'"]').animate({
			marginTop: '0.2px'
		},{
			duration: 200,
			step:function(now){
				$(this).css({transform:'scale('+(0.9+Math.sin(now*Math.PI)/6)+')'});
			},
			complete: function(){
				$('label[for="'+id+'"]').css('margin',0);
			}
		});
	});

	$('select[name="culture_match"]').change(function(){
		search_cond_add();
	});

	$('#sort-area select, #sort-area input[type=checkbox]').change(function(){
		$('form#search_cond').find("input[name='pagenum']").val(1).submit();
	});

	$(".submitBtnReset").on("click", function() {
		$("form#search_cond").find("input[type=text],input[type=number],select").val('');
		$("form#search_cond").find("input[type=checkbox]").prop('checked',false);
		search_initialize('reset');
		if(!$('input:checkbox[name="samename"]').prop("checked"))
			$('input:checkbox[name="samename"]').prop('checked',true);
	});

	// $(".detailBtn").on("click", function() {
	// 	if ($(".searchList01_term02").is(':visible')) {
	// 		$("form#search_cond .searchList01_term02").find("input[type=text],input[type=number],select").val('');
	// 		$("form#search_cond .searchList01_term02").find("input[type=checkbox]").prop('checked',false);
	// 		search_initialize('detail_reset');
	// 	}
	// });
	
	//―――――――――――――――――――――――――――――
	// 初期説明モーダル	
	//―――――――――――――――――――――――――――――
	createInfoModal();
	showInfoModal();
	// モーダル作成
	//―――――――――――――――
	function createInfoModal(){
		var html = '<div id="first-modal-wrap" class="first-modal-close">'+
			'<div id="first-modal">'+
			'<div id="first-modal-img-wrap"><div id="first-modal-img"><img src="/common/img/parts/searchform/q1.jpg">'+
			'</div></div>'+
			'<div id="first-modal-close-btn" class="first-modal-close"><img src="/common/img/parts/btn_close@2x.png">'+
			'</div></div></div>';
		$('body').append(html);
		$('#first-modal-wrap').css('visibility',"hidden");
		$first_modal_img = $('#first-modal-img>img');
		$first_modal_img.originSrc = $first_modal_img.src;
		$first_modal_img.src = "";
		$first_modal_img.bind('load',function(){
			var modal_max_height = $('#first-modal-img>img').height()+20;
			$('#first-modal').css('max-height',modal_max_height);
			$('#first-modal-wrap').css('visibility',"visible");
		});
		$first_modal_img.src = $first_modal_img.originSrc;
	}
	$(window).resize(function(){
		var modal_max_height = $('#first-modal-img>img').height()+20;
		$('#first-modal').css('max-height',modal_max_height);
	});
	// モーダル表示
	//―――――――――――――――
	function showInfoModal(){
		if(localStorage.getItem("show_first_modal") != null){
			$('#first-modal-wrap').css('visibility',"hidden");
			$('#first-modal-wrap').hide();
		}
		else{
			localStorage.setItem("show_first_modal",true);
			$('#first-modal-wrap').show();
			
		}
	}
	// モーダルクローズ
	//―――――――――――――――
	$(document).on("click",'.first-modal-close',function(e){
		if(e.target !== e.currentTarget) return;
		$('#first-modal-wrap').hide();
	});
	$(document).on("click",'#first-modal-close-btn',function(e){
		$('#first-modal-wrap').hide();
	});

});
function refresh(data) {
	let $src = $(data);
	let $src_data = $src.find("#cardlist");
	$("#cardlist").empty();
	$("#cardlist").html($src_data.html());

	let $total = $src.find("#total_count");
	$("#total_count").text($total.text());
	initPage();
}
function initPage() {
	if (typeof g_helpers !== "undefined" && g_helpers != null) {
		var $popup = $('#cardlist a[data-href]').add('.modal_popup');
		//$popup.addClass('ajax_pop');
		var $cardlinks = $(".ajax_pop");
		g_helpers.modalWindow($cardlinks, "product");
	}

	$('#cardlist .wp-pagenavi a').on('click',function(event) {
		$this = $(this);
		let $form = $("form#search_cond");
		$form.find("input[name='pagenum']").val($this.data("page"));
		scroll_pos = "#cardlist_wrap";
		$form.submit();
		return false;
	});
	$("form#search_cond [type=submit]").on('click',function(event) {
		let $form = $("form#search_cond");
		$form.find("input[name='pagenum']").val(1);
		scroll_pos = "";
	});
}
function doAjax(url, data) {
	$.ajax({
		type: "POST",
		url : url,
		data : data,
		success : function(data, dataType) {
			refresh(data);
		},
		beforeSend : function(XMLHttpRequest){
			if (scroll_pos) {
				var speed = 500;
				var position = $(scroll_pos).offset().top - 30;
				$("html, body").animate({scrollTop:position}, speed, "swing");
			}
			// 表示削除＋loading
			$("#cardlist_wrap").addClass("loading");
		},
		complete :  function(XMLHttpRequest){
			$("#cardlist_wrap").removeClass("loading");
		},
	});
}

function search_cond_add() {
	$exclude = $('.cultureExcludeWrap');
	$includeColor = $('input:checkbox[name="culture[]"]');
	$excludeColor = $('input:checkbox[name="culture_exclude[]"]');
	$colorChecked = $('input:checkbox[name="culture[]"]:checked').not('#culture06');
	var multiColor = $('#culture_cond02').prop('checked');
	$excludeWrap = $('.cultureExcludeWrap');
	$matchesWrap = $('.cultureMatchWrap');
	$matches = $matchesWrap.find('select[name="culture_match"]');

	if( multiColor && ($colorChecked.length > 0) ) {
		$includeColor.each(function(index, element){
			if ($(element).prop('checked')) {
				$excludeColor.eq(index).prop('checked', false);
				$excludeColor.eq(index).parent('li').fadeOut();
			} else {
				$excludeColor.eq(index).parent('li').fadeIn();
			}
		});
		if (($colorChecked.length > 0) && ($matches.val() != 'all') && ($matches.val() != 'all_only')) {
			if (($excludeWrap.is(':visible')) && ($excludeWrap.find('li:visible').length <= 1)) {
				$excludeWrap.slideUp();
			} else if ($excludeColor.length != $colorChecked.length) {
				$excludeWrap.slideDown();
			} else if (($excludeWrap.find('li:visible').length + $colorChecked.length) > $includeColor.length) {
				$excludeWrap.slideUp();
			}
		} else if ($excludeWrap.find('li:visible').length <= 1) {
			$excludeWrap.slideUp();
		}
	} else {
		$excludeWrap.find('input:checkbox').prop('checked', false);
		$excludeWrap.slideUp();
	}

	if( multiColor && ($colorChecked.length > 1) ) {
		$matchesWrap.slideDown();
		if (($matches.val() == 'all') || ($matches.val() == 'all_only')) {
			$excludeWrap.find('input:checkbox').prop('checked', false);
			$excludeWrap.slideUp();
		}
	} else {
		$matches.val('');
		$matchesWrap.slideUp();
	}
}

function search_initialize(role) {
	if (role != 'detail_reset') {
		$('input:checkbox[name="suggest"]').prop('checked',true);
		$('input:checkbox[value="card_name"]').prop('checked',true);
		$('input:checkbox[value="card_ruby"]').prop('checked',true);
		$('input:checkbox[value="card_text"]').prop('checked',true);
	}
	if (role == 'initial') {
		$('input:checkbox[name="samename"]').prop('checked',true);
	}
	$('input:checkbox[name="culture_cond[]"]').prop('checked',true);
	search_cond_add();
}

///検索履歴さかのぼり時の検索条件への反映
function research(data){
	//サジェスト
	$('input:checkbox[name="suggest"]').prop('checked',false);
	if(data.suggest != null) $('input:checkbox[name="suggest"]').prop('checked',true);
	//検索条件
	$('input:checkbox[name="condition"]').prop('checked',false);
	if(data.condition != null) $('input:checkbox[name="condition"]').prop('checked',true);
	if(data.condition != null) $(".orand-toggle").addClass("checked");
	//検索キーワード
	$('input:text[name="keyword"]').val("");
	if(data.keyword != null) $('input:text[name="keyword"]').val(data.keyword);
	//検索対象
	$('input:checkbox[name="keyword_type[]"]').prop('checked',false);
	if(data.keyword_type != null){
		for(const keyword_type of data.keyword_type){
			$('input:checkbox[value="'+keyword_type+'"]').prop('checked',true);
		}
	}
	//文明(単色・多色)
	$('input:checkbox[name="culture_cond[]"]').prop('checked',false);
	if(data.culture_cond != null){
		for(const culture_cond of data.culture_cond){
			$('input:checkbox[value="'+culture_cond+'"]').prop('checked',true);
		}
	}
	//文明
	$('input:checkbox[name="culture_exclude[]"]').parent('li').show();
	$('input:checkbox[name="culture[]"]').prop('checked',false);
	if(data.culture != null){
		for(const culture of data.culture){
			$('input:checkbox[value="'+culture+'"]').prop('checked',true);
		}
	}
	search_cond_add();
	//文明(含めない)
	$('input:checkbox[name="culture_exclude[]"]').prop('checked',false);
	if(data.culture_exclude != null){
		for(const culture_exclude of data.culture_exclude){
			$('input:checkbox[name="culture_exclude[]"]input:checkbox[value="'+culture_exclude+'"]').prop('checked',true);
			//search_cond_add();
		}
	}
	//多色カードの検索対象
	$('select[name="culture_match"]').val(null);
	if(data.culture_match != null) $('select[name=culture_match]').val(data.culture_match);
	//コスト(最小)
	$('input[name="cost_lower"]').val(null);
	if(data.cost_lower != null) $('input[name="cost_lower"]').val(data.cost_lower);
	//コスト(最大)
	$('input[name="cost_upper"]').val(null);
	if(data.cost_upper != null) $('input[name="cost_upper"]').val(data.cost_upper);
	//カードの種類
	$('select[name="cardtype"]').val(null);
	if(data.cardtype != null) $('select[name="cardtype"]').val(data.cardtype);
	//ツインパクト
	$('select[name="twinpact"]').val(null);
	if(data.twinpact != null) $('select[name="twinpact"]').val(data.twinpact);
	//種族
	$('select[name="race"]').val(null);
	if(data.race != null) $('select[name="race"]').val(data.race);
	//レアリティ
	$('select[name="rarity"]').val(null);
	if(data.rarity != null) $('select[name="rarity"]').val(data.rarity);
	//パワー(最小)
	$('input[name="power_lower"]').val(null);
	if(data.power_lower != null) $('input[name="power_lower"]').val(data.power_lower);
	//パワー(最大)
	$('input[name="power_upper"]').val(null);
	if(data.power_upper != null) $('input[name="power_upper"]').val(data.power_upper);
	//商品名
	$('select[name="products"]').val(null);
	if(data.products != null) $('select[name="products"]').val(data.products);
	//フォーマット
	$('select[name="format"]').val(null);
	// if(data.block != null) $('input[name="format"]').val(data.format);
	if(data.format != null) $('select[name="format"]').val(data.format);
	//イラストレーター
	$('select[name="illustauthor"]').val(null);
	if(data.illustauthor != null) $('select[name="illustauthor"]').val(data.illustauthor);
	//特殊能力
	$('select[name="ability"]').val(null);
	if(data.ability != null) $('select[name="ability"]').val(data.ability);	
	//並び替え
	$('select[name="sort"]').val(data.sort);
	//同名カードを表示する
	$('input:checkbox[name="samename"]').prop('checked',false);
	if(data.samename != null) $('input:checkbox[name="samename"]').prop('checked',true);
	
	//詳細設定がされていれば表示
	// if( data.culture_cond != null || data.culture != null || data.culture_exclude != null || data.culture_match != null || data.cost_lower != null || data.cost_upper != null ||
	// 	data.cardtype != null || data.twinpact != null || data.race != null || data.rarity != null || data.ability != null || data.power_lower != null || data.power_upper != null || data.products != null ||
	// 	data.format != null || data.illustauthor != null){
	// 	$(".searchList01_term02").slideDown("fast");
	// 	if($(".detailBtn").hasClass("current")) {
	// 		$(".detailBtn").addClass('current');
	// 	}
	// }else{
		$(".searchList01_term02").slideUp("fast");
		$(".detailBtn").removeClass('current');
	// }
	
	//検索
	doAjax("/card/", data, ".sectionFormat05");
}

///ブラウザ戻る・進むで検索をさかのぼる
window.addEventListener('popstate',function(e){
	if(e.state){
		research(e.state);
	}
	else{
		window.location.reload();
	}
});