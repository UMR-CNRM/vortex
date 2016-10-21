
var sub_xmlhttp = new Array();

var arr_class=new Array;
var arr_collection =new Array; 
arr_collection[0]="";
var arr_type_value=new Array;
//////////////table to store the options uses by the user/////////////////

var attri =new Array;
var tab =new Array;
var tab2=new Array;
var collections=new Array;
var packages=new Array;
var types_checked=new Array;
var compteur=0;
var text='';
var level="DEFAULT";
var arr_attr =new Array();

var arr_css_partial=new Array();
var arr_css_full=new Array();

jQuery(function(){
//////////////////////////////////////////////////////////////////Load the XML export////////////////////////////////////////////////////////////////

    var spin_opts = {
        scale: 4 // Scales overall size of the spinner
    };
    var spinner = new Spinner(spin_opts).spin();
    jQuery( spinner.el ).appendTo( "#loading1_body" );

    xmlhttp = new XMLHttpRequest();
    xmlhttp.open("GET","_ExportXML/tbinterface.xml", async=true);
    xmlhttp.onreadystatechange = function () {
        if(xmlhttp.readyState === XMLHttpRequest.DONE && xmlhttp.status === 200) {
            deffered_init(xmlhttp.responseXML);
        }
    };
    xmlhttp.send(null);
});

function deffered_init(xml_doc) {

    var col= xml_doc.getElementsByTagName('collector');
    for(var i=0;i<col.length;i++){
        arr_collection[i+1]=col[i].getAttribute('name');   
    }

    // recuperer les differents fichiers d'un coup... ne finir l'initialisation
    // que quand tout est fini.
    for(var j=1;j<arr_collection.length;j++){
        sub_xmlhttp[j] = new XMLHttpRequest();
        sub_xmlhttp[j].open("GET","_ExportXML/tbinterface_"+arr_collection[j]+".xml", async=true);
        sub_xmlhttp[j].onreadystatechange = function (evt) {
            if(evt.target.readyState === XMLHttpRequest.DONE && evt.target.status === 200) {
                // On verifie les autres XML
                var alldone = true;
                for (var k=1;k<arr_collection.length;k++){
                    alldone = alldone && (sub_xmlhttp[k].readyState === XMLHttpRequest.DONE && sub_xmlhttp[k].status === 200);
                }
                if (alldone) {
                    finalise_init();
                }
            }
        };
    }
    for(var j=1;j<arr_collection.length;j++){
        sub_xmlhttp[j].send();
    }

    // Les intialisations suivantes ne dépendent pas de la lecture des XML

    /////////////////////////////////Mise en place des boites de recherche ////////////////////////////////////////////////:
    ///créer un multi-rechercher avec plusieurs attributs
    function split( val ) {
        return val.split( /,\s*/ );
    }
    function extractLast( term ) {
        return split( term ).pop();
    }
    //////les boites à recherche
    jQuery( "#RechercheAttr" )
        // don't navigate away from the field on tab when selecting an item
        .on( "keydown", function( event ) {
            if ( event.keyCode === jQuery.ui.keyCode.TAB &&
                jQuery( this ).autocomplete( "instance" ).menu.active ) {
            event.preventDefault();
            }
        })
        .autocomplete({
            minLength: 1,
            source: function( request, response ) {
                // delegate back to autocomplete, but extract the last term
                response(jQuery.ui.autocomplete.filter(autocomplete_table(),
                                                       extractLast( request.term )));
            },
            focus: function() {
            // prevent value inserted on focus
                return false;
            },
            delay: 100,
            select: function( event, ui ) {
                var terms = split( this.value );
                // remove the current input
                terms.pop();
                // add the selected item
                terms.push( ui.item.value );
                // add placeholder to get the comma-and-space at the end
                terms.push( "" );
                this.value = terms.join( ", " );
                text =this.value;
                return false;
            }

        });

    var tw_options = {
        callback: function (value) {
           find_cl_at();
        }, 
        wait: 500,
        highlight: true,
        allowSubmit: true,
        captureLength: 2
    }
    
    ///récupérer ce qui est taper dans "rachercher par classe"
    jQuery("#RechercheCl").typeWatch( tw_options );

    //récupperer les attributs recherehé
    jQuery("#RechercheAttr").typeWatch( tw_options );

}

function finalise_init() {

    ////////////////////////result of load :array_packages (table of the packages) arr_collectors(table of coleector's name)
    for(var j=1;j<arr_collection.length;j++){
        var xml_dom = sub_xmlhttp[j].responseXML;
        arr_class[j-1] = xml_dom.getElementsByTagName("class");
        delete sub_xmlhttp[j];
    }

    ///////////////////////////////make the selector of packages////////////////////////////////////////////////////
    ///local variables
    var package_table=new Array; //to co,nstruct the packages name from the xml files (vortex,iga,gco.......)
    var cmpt=0;
    var c=0;
    for(var j=0;j<arr_class.length;j++){
        for(var i=0;i<arr_class[j].length;i++){
            var aux =arr_class[j][i].getAttribute('name');
            attri[c] =arr_class[j][i].getElementsByTagName("attr");
            c++;
            if(aux!=null) {
            var classe=aux.substring(0,aux.indexOf('.'));
                if( package_table.indexOf(classe)==-1){
                    package_table[cmpt]=classe;
                    cmpt++;
                    jQuery( '<option value='+classe+' selected="selected">'+classe+'</option>' ).appendTo( ".cl" );
                }
            }         
        }
    }

    ////////////////////////////////////construct the table of autocomplete (table of attributs)//////////////////
    tab_attr=new Array;//the table of all attributes
    cp=0;
    for(var i=0;i<attri.length;i++){
        for(var j=0;j<attri[i].length;j++){
            tab_attr[cp]=attri[i][j].getAttribute('name');
            cp++;
        }
    }
    //supprimer les occurence dans tabs attr
    for(var i=0;i<tab_attr.length;i++){
        var aux=tab_attr[i];
        for(var j=i+1;j<tab_attr.length;j++){
            if(aux.indexOf(tab_attr[j])!=-1){
                tab_attr[j]='-1';
            }
        }
    }
    var arr_attr =new Array;
    var c=0;
    for(var i=0;i<tab_attr.length;i++){
        if(tab_attr[i]!='-1'){
            arr_attr[c]=tab_attr[i];
            c++;
        }
    }

    /////////////////////////////////cas par défaut :toutes les arbres sont construits

    ////////// setup the collectors multiselect //////////////
    for(var i=1;i<arr_collection.length;i++){
        jQuery( '<option value='+i+' name='+i.toString()+' selected="selected">'+arr_collection[i]+'</option>' ).appendTo( ".col" );
    }
    jQuery(".col").multiselect({
        includeSelectAllOption: true,
        onChange: function(option, checked, select) {
            var ind=jQuery(option).val()-1;
            if(checked){
                make_tree_blugin(ind);
                find_cl_at();
            }
            else {
                jQuery('#jstree'+ind).remove();    
            }
        },
        onSelectAll: function(checked){
            for(var i=0;i<arr_class.length;i++){
                jQuery('#jstree'+i).remove();
            }
            if (checked) {
                for(var i=0;i<arr_class.length;i++){
                    make_tree_blugin(i);
                }
                find_cl_at();
            }
        },
    });

    ////////// setup the package multiselect //////////////
    packages=package_table.slice(0);
    jQuery(".cl").multiselect({
        includeSelectAllOption: true,
        onChange: function(option, checked, select) {
            var value = jQuery(option).val();
            if(checked){
                packages.push(value); 
            }
            else{
                for(var i=0;i<packages.length;i++){
                    if(packages[i].indexOf(value)!=-1){
                        packages.splice(i,1);
                    }
                }
            }
            disable_class();
        },
        onSelectAll: function(checked){
            if (checked){
                packages=package_table.slice(0);
            } else {
                packages=new Array;
            }
            disable_class();
        },
    });

    jQuery( "#loading1_body" ).empty();
    jQuery( "#loading1" ).hide();
    jQuery( "#wrapper" ).show();
};

function get_re_attr_tab() {

    var re_attri =  jQuery("#RechercheAttr").val()
    var attr_tab_tmp = re_attri.split(",");
    var attr_tab = new Array;
    for(var i=0;i<attr_tab_tmp.length;i++){
        if (attr_tab_tmp[i].trim() != "") {
            attr_tab.push(attr_tab_tmp[i].trim());
        }
    }
    return attr_tab;
}

//make_tree_blugin :créer un arbre qui correspond à l'indice i
// input: i :indice du collecteur
// 0:containers,1 providers,2 resources ,3 :components 
function make_tree_blugin(i){
    makeTree(i);
    jQuery('#jstree'+i).on('changed.jstree', function (e, data) {
        var attri_tab = get_re_attr_tab();
        for(i = 0, j = data.selected.length; i < j; i++) {
            var cl_name=data.instance.get_node(data.selected[i]).text;
            jQuery('#ele'+makeId(cl_name)).remove();
            makeTable(cl_name,gl_var,ct);
            gl_var++;
            ct++;
            for(var i=0;i<attri_tab.length;i++){
                jQuery('.'+attri_tab[i].trim()).css('background-color','#90EE90');
            }  
        }
    }).jstree();
    process_abstracts(i)
}

function process_abstracts(i) {
    // Find abstract classes...
    for(var j=0;j<arr_class[i].length;j++){
        var aux2 = arr_class[i][j].getElementsByTagName('footprint');
        if ( aux2.length > 0 ) {
            var val = aux2[0].getAttribute('abstract');
            if( val!=null && val.indexOf("True")!=-1){
                var cl_name= arr_class[i][j].getAttribute("name");
                var thenode = jQuery('#jstree'+i).jstree().get_node(makeId(cl_name))
                thenode.a_attr["class"] += " treeabstract";
                jQuery("#"+makeId(cl_name)+"_anchor").addClass("treeabstract");
            }
        }
    }
}

//rénitilaiser le css 'couleur vert' quand on recommence la recherche
function reset_style(){
    for(var i=0;i<arr_css_partial.length;i++){
        var thenode = jQuery('#jstree'+arr_css_partial[i].tree).jstree().get_node(arr_css_partial[i].id);
        if (thenode && typeof thenode.a_attr["class"] !== typeof undefined && thenode.a_attr["class"] !== false ) {
            var lclasses = thenode.a_attr["class"].trim().split(' ');
            thenode.a_attr["class"] = '';
            for(var j=0;j<lclasses.length;j++){
                if(lclasses[j] != 'treepartial') {
                    thenode.a_attr["class"] += ' ' + lclasses[j];
                }
            }
            jQuery('#' + arr_css_partial[i].id + "_anchor").removeClass('treepartial');
        }
    }
    for(var i=0;i<arr_css_full.length;i++){
        var thenode = jQuery('#jstree'+arr_css_full[i].tree).jstree().get_node(arr_css_full[i].id);
        if (thenode && typeof thenode.a_attr["class"] !== typeof undefined && thenode.a_attr["class"] !== false ) {
            var lclasses = thenode.a_attr["class"].trim().split(' ');
            thenode.a_attr["class"] = '';
            for(var j=0;j<lclasses.length;j++){
                if(lclasses[j] != 'treefull') {
                    thenode.a_attr["class"] += ' ' + lclasses[j];
                }
            }
            jQuery('#' + arr_css_full[i].id + "_anchor").removeClass('treefull');
        }
    }
    arr_css_partial = new Array();
    arr_css_full = new Array();
}

//désactiver les packages qui ne correspond pas à la rechercher
function disable_class(){

    for(var l=0;l<arr_class.length;l++){
        for(var j=0;j<arr_class.length;j++){
            for(var i=0;i<arr_class[j].length;i++){
                if(document.getElementById('jstree'+l)!=null) {
                    var aux= arr_class[j][i].getAttribute('name');  
                    if(aux!=null){         
                        jQuery('#jstree'+l).jstree(true).disable_node(makeId(aux));
                    }
                }
            }
        }
    }   

    for(var l=0;l<arr_class.length;l++){
        for(var j=0;j<arr_class.length;j++){
            for(var i=0;i<arr_class[j].length;i++){
                for(var k=0;k<packages.length;k++){
                    if(document.getElementById('jstree'+l)!=null) {
                        var aux= arr_class[j][i].getAttribute('name');  
                        if(aux!=null && aux.indexOf(packages[k])!=-1){         
                            jQuery('#jstree'+l).jstree(true).enable_node(makeId(aux));
                        }
                    }
                }
            }
        }
    }

    find_cl_at();
}

//////////////////////////////// contruction de l'arbre////////////////////////////////////////////

//créer l'id d'une classe à partir de son nom
function makeId(cl){
    var tb =cl.split(".");
    return tb[tb.length-1];
}

//vérifier si une base est une classe qui hérite ou il n'hérite pas
function is_class(classe_name){
    var boolean = false;
    for(var i=0;i<arr_class.length;i++){
        for(var j=0;j<arr_class[i].length;j++){
            var name= arr_class[i][j].getAttribute("name");
            if(name!=null && name==classe_name.trim()){
                boolean=true;
            }
        }
    }
    return boolean;
}

//rec_make_tree:fonction récursif qui permet de créer l'arbre à partir de la racine(footprint)
function rec_makeTree(ele_inserer,a,ide){

    if(ele_inserer.length==0){
        var tree=arr_class[a];

        for(var i=0;i<tree.length;i++){
            var bases=tree[i].getElementsByTagName('bases');

            for(var j=0;j<bases.length;j++){
                var base =bases[0].getElementsByTagName('base');

                if(is_class(base[0].textContent)==false){
                    var cl_name=tree[i].getAttribute("name");
                    var id=makeId(cl_name);
                    jQuery('<ul id="tr'+ide+'"></ul>').appendTo("#jstree"+a);
                    jQuery('<li id="'+id+'">'+cl_name+'</li>').appendTo('#tr'+ide);
                    jQuery('<ul class="'+id+'"></ul>').appendTo('#'+id);
                    ele_inserer.push(cl_name);
                    rec_makeTree(ele_inserer,a);
                }
           }
        }
    }
    else{

        for(var l=0;l<ele_inserer.length;l++){
            var tree=arr_class[a];

            for(var i=0;i<tree.length;i++){
                var bases=tree[i].getElementsByTagName('bases');

                for(var j=0;j<bases.length;j++){
                    var base =bases[0].getElementsByTagName('base');
                    
                    for(k=0;k<base.length;k++){
                        if(base[k].textContent.indexOf(ele_inserer[l])!=-1){
                            var cl_name=tree[i].getAttribute("name");
                            var id=makeId(cl_name);
                            jQuery('<li id="'+id+'">'+cl_name+'</li>').appendTo('.'+makeId(ele_inserer[l]));
                            jQuery('<ul class="'+id+'"></ul>').appendTo('#'+id);
                            ele_inserer.push(cl_name);
                        }
                    }
                }
            }
        }
    }
}

//pour paramétriser la fonction rec_make_tree
function makeTree(vari){
    var ele_inserer=new Array;
    
    var id="tree"+vari;
    var id2="jstree"+vari;
    
    jQuery('<div id="'+id2+'"></div>').appendTo("#resource");
    
    rec_makeTree(ele_inserer,vari,id);
    jQuery('#'+id).jstree();
    
    compteur++;
}

function appartient(element,tableau){
    var b=false;
    var c_app=0;
    for(var i=0;i<tableau.length;i++){
        if(element.trim()==tableau[i].trim()){
            c_app++;
        }
    }
    if(c_app!=0){
        b=true;
    }
    return b;
}

//fonction qui permet de voir si tab1 est inclu dans tab2
function appartient_tab(tab1,tab2){
    var c=0;
    var boolean=false;
    for(var i=0;i<tab1.length;i++){
        if(appartient(tab1[i],tab2)){
            c++;
        }
    }
    if(c > 0 && c==tab1.length){
        boolean=true;
    }
    return boolean;
}

//récuppere les attributs d'une classe d'indice j,i dans arr_class
function get_attributes(j,i){
    var aux =arr_class[j][i].getAttribute('name');
    var att=arr_class[j][i].getElementsByTagName("attr");
    var class_attri=new Array();
    for(var k=0;k<att.length;k++){
        if (attribut_level(att[k])) {
            class_attri.push(att[k].getAttribute('name'));
        }
    }
    return class_attri;
}

//fonction recherche dans l'arbre qui permet de donner le résultat fibnal du filtarge
function find_cl_at(){

    var re_class = jQuery("#RechercheCl").val().trim()
    var attri_tab=get_re_attr_tab();

    reset_style();

    for(var j=0;j<arr_class.length;j++){
        if (document.getElementById('jstree'+j)!=null) {
            jQuery('#jstree'+j).jstree(true).close_all();
        }
        for(var i=0;i<arr_class[j].length;i++){
            var cl_name=arr_class[j][i].getAttribute("name");
            if(packages.length != 0 && cl_name != null){
                //////////////////////////////
                var min_cl=cl_name.toLowerCase();
                for(var k=0;k<packages.length;k++){
                    if(min_cl.indexOf(packages[k])!=-1 && min_cl.indexOf(re_class.toLowerCase())!=-1){
                        var att_class = get_attributes(j,i);
                        var ident= makeId(cl_name);
                        var positve_match = false;
                        if(appartient_tab(attri_tab,att_class)){
                            arr_css_full.push({tree: j, id: ident});
                            positve_match = true;
                        } else {
                            if (re_class != "") {
                                arr_css_partial.push({tree: j, id: ident});
                                positve_match = true;
                            }
                        }
                        if(document.getElementById('jstree'+j)!=null && positve_match) {
                            p_node = jQuery('#jstree'+j).jstree(true).get_path(makeId(cl_name));
                            for (var node=0; node<p_node.length-1; node++) {
                                 jQuery('#jstree'+j).jstree(true).open_node(makeId(p_node[node]));
                            }
                        }
                    }
                }
            ////////////////////////
            }
        }
    }
    if(self.packages.length > 0 && arr_css_partial.length + arr_css_full.length == 0 && re_class != ""){
        alert("Les informations que vous avez fournis ne correspondent à aucune classe");
    }
    for(var i=0;i<arr_css_partial.length;i++){
        jQuery('#jstree'+arr_css_partial[i].tree).jstree().get_node(arr_css_partial[i].id).a_attr["class"] += " treepartial";
        jQuery('#' + arr_css_partial[i].id + "_anchor").addClass('treepartial')
    }
    for(var i=0;i<arr_css_full.length;i++){
        jQuery('#jstree'+arr_css_full[i].tree).jstree().get_node(arr_css_full[i].id).a_attr["class"] += " treefull";
        jQuery('#' + arr_css_full[i].id + "_anchor").addClass('treefull')
    }
}

//montrer les attributs de la classe
function show_table(form_element){
    jQuery('#ul'+form_element.id).show();
}
//maquer les attributs
function hide_table(form_element){
    jQuery('#ul'+form_element.id).hide();
}
//supprimer le tableau
function remove_table(form_element){
    jQuery('#'+form_element.id).remove();
}
// redirection vers la page d'information
function RedirectionJavascript(form_element){
    var ref=form_element.id.split(".");
    window.open('../../library/'+ref[0]+'/'+ref[1]+'/'+ref[2]+'.html#'+form_element.id); 
}
//créer les bouttons pour agir sur le tableau
function make_button_action(ct,id_tab,value,info){

    var html_button ='<div class="pull-right">';

    html_button+=' <button  type="button" class="btn btn-default btn-circle" data-toggle="tooltip" data-placement="top" title="'+info+'">';
    html_button+='<i class="fa  fa-info " style="color:#31B0D5"></i>';
    html_button+='</button>';

    html_button+='<button type="button"  id="'+value+'" onClick="RedirectionJavascript(this)" class="btn btn-default btn-circle"   >';
    html_button+='<i class="fa  fa-link " style="color:#31B0D5"></i>';
    html_button+='</button>';

    html_button+='<button type="button" id="'+ct+'" class="btn btn-default btn-circle" onClick="hide_table(this)" >';
    html_button+='<i class="fa  fa-compress " style="color:#C9302C"></i>';
    html_button+='</button>';

    html_button+='<button type="button" id="'+ct+'" class="btn btn-default btn-circle" onClick="show_table(this)">';
    html_button+='<i class="fa  fa-expand " style="color:#449D44"></i>';
    html_button+='</button>';

    html_button+='<button type="button" id="'+id_tab+'" class="btn btn-default btn-circle" onClick="remove_table(this)">';
    html_button+='<i class="fa fa-times  " style="color:#EC971F"></i>';    
    html_button+='</button>';
     
    html_button+='</div>';                    
    return html_button;
}

//créer le tableau
function makeTable(value,gl_var,ct){
    var attr=new Array();
    var a=0;
    var b=0;

    for(var j=0;j<arr_class.length;j++){
        for(var i=0;i<arr_class[j].length;i++){
            if(arr_class[j][i].getElementsByTagName('name')!=null){
                if(arr_class[j][i].getAttribute('name')==value ){
                    attr =arr_class[j][i].getElementsByTagName("attr");
                    //////////////////////
                    a=j;
                    b=i;
                    /////////////////////////  
                }
            }
        }
    }

    var id_tab="ele"+makeId(value);
    jQuery('<div class="panel panel-default" id="'+id_tab+'" ></div>').appendTo("#tbs");
    var aux2=arr_class[a][b].getElementsByTagName('footprint');
    var val=  aux2[0].getAttribute('abstract');
    if(val!=null && val.indexOf('True')!=-1){
        jQuery('<div class="abstraite panel-heading" id="ph'+id_tab+'">'+value+'</div>').appendTo('#'+id_tab);
    }
    else{
        jQuery('<div class="panel-heading" id="ph'+id_tab+'">'+value+'</div>').appendTo('#'+id_tab);
    }
    jQuery('<ul class="nav nav-tabs" id="list'+ct+'"></ul>').appendTo('#'+id_tab);
    //make the body 
    jQuery('<div class="panel-body" id="ul'+ct+'"></div>').appendTo('#'+id_tab); 
    //liste of attributes
    //function show and hide
    var aux=arr_class[a][b].getElementsByTagName('info');
    var info=aux[0].textContent;
    var button=make_button_action(ct,id_tab,value,info);
    jQuery(button).appendTo("#ph"+id_tab);

    for(var i=0;i<attr.length;i++){
        if(attribut_level(attr[i])){ 
            var ref="#tab-"+i+"_"+ct;
            var element_optional=attr[i].getElementsByTagName("optional");
            if(element_optional[0].textContent.indexOf("False")!=-1){
                jQuery('<li><a  data-toggle="tab" href='+ref+'  class="'+attr[i].getAttribute('name')+' obligatoire">'+attr[i].getAttribute('name')+'</a></li>').appendTo('#list'+ct);
            }
            else{
                jQuery('<li ><a data-toggle="tab" href='+ref+' class="'+attr[i].getAttribute('name')+' attribut">'+attr[i].getAttribute('name')+'</a></li>').appendTo('#list'+ct);
            }
        }
    }

    jQuery('<div class="tab-content" id="tabs'+ct+'"></div>').appendTo('#ul'+ct);

    for(var i=0;i<attr.length;i++){
        ///////////////////
        if(attribut_level(attr[i])){ 
            var id="tab-"+i+"_"+ct;
            if(i==0){
                jQuery('<div class="tab-pane fade in active" id="'+id+'"></div>').appendTo('#tabs'+ct);
            }
            else{
                jQuery('<div class="tab-pane fade" id="'+id+'"></div>').appendTo('#tabs'+ct);
            }

            ///////////////////////////////
            var element_optional=attr[i].getElementsByTagName("optional");
            var html_tab='<table id="id_tab" align="left"><tr><th></th>';
 
            //////////////////////////remap/////////////////////////////////
            var element_values=attr[i].getElementsByTagName("values");
            var str_value ='none';
            if(element_values.length>0){
                str_value='';
                for(var k=0;k< element_values.length;k++){     
                    str_value +=element_values[k].textContent+" ";      
                }
            }
            if(str_value!="none"){
                html_tab+='<tr><td>'+"<h style='color:red'> values:</h>"+str_value+'</td><td>';
            }

            /////////////////default value////////////
            var element_default=attr[i].getElementsByTagName("default"); 
            for(var k=0;k< element_default.length;k++){
                if(element_default[k].textContent.indexOf("None")==-1){
                    html_tab+='<tr><td>'+"<h style='color:red'> default: </h>"+element_default[k].textContent+'</td><td>';
                }        
            }

            //////////////////////alias/////////////////
            var element_alias=attr[i].getElementsByTagName("alias");
            var str_alias ='';
            if(element_alias.length>0){
                str_alias='';
                for(var k=0;k< element_alias.length;k++){
                    str_alias +=element_alias[k].textContent+" ";      
                }
                html_tab+='<tr><td>'+"<h style='color:red'>alias:</h>"+str_alias+'</td><td>';
            }

            /////////////////// access/////////////////
            var element_access=attr[i].getElementsByTagName("access");   
            for(var k=0;k< element_access.length;k++){
                if(element_access[k].textContent.indexOf('rxx')==-1){
                    html_tab+='<tr><td>'+" <h style='color:red'> access:</h>"+element_access[k].textContent+'</td><td>';
                }
            }

            ////////////////////// info////////////////////////
            var element_info=attr[i].getElementsByTagName("info");    
            for(var k=0;k< element_info.length;k++){
                    html_tab+='<tr><td>'+"<h style='color:red'> info:</h>"+element_info[k].textContent+'</td><td>';
            }     
            html_tab += '</table>'; 

            document.getElementById(id).innerHTML = html_tab;
        }
    }
}   

var gl_var=0;
var ct=1;            

function rm(){
    document.getElementById('tbs').innerHTML =''; 
}

/////////////////////////////////////level of user////////////

function class_level_default(){
    level="DEFAULT";
    document.getElementById("user_mode").removeAttribute("class");
    jQuery("#user_mode").addClass("glyphicon glyphicon-pawn");
}
function class_level_advanced(){
    level="ADVANCED";
    document.getElementById("user_mode").removeAttribute("class");
    jQuery("#user_mode").addClass("glyphicon glyphicon-knight");
}
function class_level_guru(){
    level="GURU";
    document.getElementById("user_mode").removeAttribute("class");
    jQuery("#user_mode").addClass("glyphicon glyphicon-king");
}

function attribut_level(attri){
    var bool=true;
    var levxml=attri.getElementsByTagName("doc_visibility");
    var lev=levxml[0].getElementsByTagName("overview");
    if ((lev[0].textContent.indexOf("GURU")  != -1 &&
            (level == "DEFAULT" || level == "ADVANCED")) ||
        (lev[0].textContent.indexOf("ADVANCED")  != -1 &&
            (level == "DEFAULT")) ) {
        bool=false;
    }
    return bool
}

function redirection(){
    window.open('faq/index.html');
}

function autocomplete_table(){
    var attri_level=new Array();
    var cmpt=0
    for(var j=0;j<arr_class.length;j++){
        for(var i=0;i<arr_class[j].length;i++){
            if(arr_class[j][i].getElementsByTagName('name')!=null){
                attr =arr_class[j][i].getElementsByTagName("attr");
                for(var k=0;k<attr.length;k++){
                    var name_attr=attr[k].getAttribute('name');
                    if(attribut_level(attr[k]) && appartient(name_attr,attri_level)==false){
                        attri_level[cmpt]=name_attr;
                        cmpt++;
                    }
                }
            }
        }
    }
    return attri_level;
}
