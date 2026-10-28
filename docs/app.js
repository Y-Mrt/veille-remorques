(function () {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const euro = new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
  const dateFmt = new Intl.DateTimeFormat("fr-FR", { weekday: "long", day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" });
  const shortFmt = new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "short" });
  let data = null;

  // Sur GitHub Pages (owner.github.io/repo/), le dépôt se déduit de l'adresse.
  let repo = "";
  if (location.hostname.endsWith(".github.io")) {
    const seg = location.pathname.split("/").filter(Boolean)[0];
    if (seg) repo = location.hostname.split(".")[0] + "/" + seg;
  }
  if (repo) {
    $("#apk").href = "https://github.com/" + repo + "/releases/latest/download/veille-remorques.apk";
  } else {
    $("#apk").parentElement.hidden = true;
  }

  function parse(d) { const t = d ? new Date(d) : null; return t && !isNaN(t) ? t : null; }
  function isNew(a) { return a.en_ligne !== false && data.last_ok_run_at && a.first_seen === data.last_ok_run_at; }

  function ptacText(a) {
    if (a.ptac_kg) return (a.ptac_kg / 1000).toLocaleString("fr-FR", { maximumFractionDigits: 2 }) + " t";
    return (a.essieux || 2) + " ess.";
  }
  function ptacSource(a) {
    if (a.ptac_kg) return a.ptac_source || "PTAC indiqué";
    return a.ptac_source || "PTAC non indiqué, 2 essieux vus sur les photos";
  }

  function spec(ul, label, val) {
    if (val === undefined || val === null || val === "") return;
    const li = document.createElement("li");
    if (val === true) { li.textContent = label; li.className = "yes"; }
    else if (val === false) { li.textContent = label; li.className = "no"; }
    else li.textContent = label + " : " + val;
    ul.appendChild(li);
  }

  function card(a) {
    const node = $("#tpl").content.firstElementChild.cloneNode(true);
    if (isNew(a)) node.classList.add("is-new");
    const imgA = node.querySelector(".ad__img");
    imgA.href = a.url;
    const img = imgA.querySelector("img");
    if (a.image) { img.src = a.image; img.alt = a.titre || ""; } else imgA.removeChild(img);
    const t = node.querySelector(".ad__title a");
    t.href = a.url; t.textContent = a.titre || "Annonce Leboncoin";
    node.querySelector(".ad__price").textContent = a.prix != null ? euro.format(a.prix) : "Prix ?";
    const where = [a.ville, a.departement ? "(" + a.departement + ")" : ""].filter(Boolean).join(" ");
    node.querySelector(".ad__where").textContent =
      (where || "Lieu non précisé") + (a.distance_km != null ? ", à environ " + Math.round(a.distance_km) + " km de Sarlat" : "");
    node.querySelector(".ad__plate-val").textContent = ptacText(a);
    node.querySelector(".ad__src").textContent = ptacSource(a);
    const ul = node.querySelector(".ad__specs");
    spec(ul, "Freinée", a.freinage);
    spec(ul, "Treuil", a.treuil);
    spec(ul, "Rampes", a.rampes);
    spec(ul, "Carte grise", a.carte_grise);
    spec(ul, "État", a.etat);
    node.querySelector(".ad__notes").textContent = a.points || "";
    const pub = parse(a.date_publication), seen = parse(a.first_seen), gone = parse(a.retiree_le);
    const bits = [];
    if (pub) bits.push("Publiée le " + shortFmt.format(pub));
    if (seen) bits.push("repérée le " + shortFmt.format(seen));
    if (gone) bits.push("retirée le " + shortFmt.format(gone));
    node.querySelector(".ad__dates").textContent = bits.join(", ");
    return node;
  }

  function render() {
    const f = new FormData($("#filters"));
    const vue = f.get("vue"), tri = f.get("tri"), dist = Number(f.get("dist"));
    const online = data.annonces.filter((a) => a.en_ligne !== false);
    const gone = data.annonces.filter((a) => a.en_ligne === false);
    const nbNew = online.filter(isNew).length;
    $("#nb-new").textContent = nbNew ? nbNew : "";

    let list = online.filter((a) => vue !== "nouvelles" || isNew(a));
    if (dist) list = list.filter((a) => a.distance_km == null || a.distance_km <= dist);
    const by = {
      recent: (a, b) => (b.date_publication || b.first_seen || "").localeCompare(a.date_publication || a.first_seen || ""),
      prix: (a, b) => (a.prix ?? 1e9) - (b.prix ?? 1e9),
      distance: (a, b) => (a.distance_km ?? 1e9) - (b.distance_km ?? 1e9),
    };
    list.sort(by[tri]);

    const ol = $("#list"); ol.replaceChildren(...list.map(card));
    const empty = $("#empty");
    if (!list.length) {
      empty.hidden = false;
      empty.textContent = !online.length
        ? "Aucune annonce vérifiée pour l'instant. La prochaine vérification a lieu à 8 h 15 ou 19 h 15."
        : vue === "nouvelles"
          ? "Pas de nouvelle annonce depuis le dernier passage. Choisissez « Toutes » pour voir celles encore en ligne."
          : "Aucune annonce dans ce rayon. Élargissez la distance.";
    } else empty.hidden = true;

    $("#gone").hidden = !gone.length;
    $("#nb-gone").textContent = gone.length;
    $("#list-gone").replaceChildren(...gone.map(card));

    const recos = (data.recommandations || [])
      .map((r) => ({ r, a: online.find((a) => a.id === r.id) })).filter((x) => x.a);
    $("#reco").hidden = !recos.length;
    $("#reco-list").replaceChildren(...recos.map(({ r, a }) => {
      const li = document.createElement("li");
      const link = document.createElement("a");
      link.href = a.url; link.target = "_blank"; link.rel = "noopener";
      link.textContent = (a.titre || "Annonce") + ", " + (a.prix != null ? euro.format(a.prix) : "");
      li.append(link, r.raison ? " : " + r.raison : "");
      return li;
    }));
  }

  function renderStatus() {
    const s = $("#status"), lr = data.last_run;
    s.classList.remove("is-warn");
    if (!lr) { s.textContent = "La veille n'a pas encore publié de résultats."; return; }
    const when = parse(lr.run_at);
    let txt = "Dernier passage " + (when ? dateFmt.format(when) : "") + ". ";
    if (lr.status !== "ok") {
      s.classList.add("is-warn");
      txt += "Vérification impossible : " + (lr.message || "Leboncoin n'a pas pu être consulté") + ". Les annonces ci-dessous datent du dernier passage réussi.";
    } else {
      txt += lr.nb_en_ligne + " annonce" + (lr.nb_en_ligne > 1 ? "s" : "") + " en ligne, " +
        lr.nb_nouvelles + " nouvelle" + (lr.nb_nouvelles > 1 ? "s" : "") + ".";
    }
    s.textContent = txt;
  }

  $("#filters").addEventListener("change", render);

  fetch("data/annonces.json?t=" + Date.now(), { cache: "no-store" })
    .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then((d) => { data = d; data.annonces = data.annonces || []; renderStatus(); render(); })
    .catch(() => {
      $("#status").textContent = "Les annonces n'ont pas pu être chargées. Vérifiez la connexion puis rechargez la page.";
      $("#status").classList.add("is-warn");
    });
})();
