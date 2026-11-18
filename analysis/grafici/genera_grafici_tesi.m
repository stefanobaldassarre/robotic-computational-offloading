function genera_grafici_tesi()
% GENERA_GRAFICI_TESI Nove figure G1-G9 per la tesi, senza toolbox aggiuntivi.
% Avvio in MATLAB Online: genera_grafici_tesi
% I CSV devono essere nella sottocartella dati_grafici accanto a questo file.
% SD = deviazione standard campionaria fra cinque repliche (non IC95%).
% Le verifiche funzionali G8/G9 hanno UNA osservazione per modalita'.

baseDir = fileparts(mfilename('fullpath'));
dataDir = fullfile(baseDir, 'dati_grafici');
assert(isfolder(dataDir), 'Manca la sottocartella dati_grafici.');
assert(exist('exportgraphics','file') ~= 0, ...
    'Serve una versione MATLAB con exportgraphics (R2020a o successiva).');
runID = char(datetime('now', 'Format', 'yyyyMMdd_HHmmss_SSS'));
outDir = fullfile(baseDir, ['grafici_' runID]);
assert(~isfolder(outDir), 'Cartella output gia'' presente: rilanciare.');
mkdir(outDir);

T = readStrings(fullfile(dataDir, 'tempi_per_replica.csv'));
R = readStrings(fullfile(dataDir, 'resources_per_run.csv'));
M = readStrings(fullfile(dataDir, 'movimento_sintesi.csv'));
TS = readStrings(fullfile(dataDir, 'tempi_sintesi.csv'));
RS = readStrings(fullfile(dataDir, 'resources_summary.csv'));
assert(height(T) == 180, 'Attese 180 righe metrica/replica nei tempi.');
assert(height(R) == 70, 'Attesi 70 blocchi risorse.');
assert(height(M) == 4, 'Attese quattro prove funzionali selezionate.');
validateSummaries(T, R, TS, RS);

modes = ["local", "remote"];
C = [0.0902 0.4078 0.6471; 0.8078 0.3490 0.1176];
fontName = 'Arial';
figNames = strings(9,1);

%% G1 - A: processing ed E2E
[f,t] = makeFigure(1,2,14.5,7.3);
metrics = ["processing_ms", "e2e_ms"];
titles = ["Processing", "E2E Ubuntu"];
for k = 1:2
    ax = nexttile(t);
    v = cell(1,2);
    for m = 1:2
        v{m} = timeValues(T, "a", metrics(k), modes(m), "all");
    end
    barComparison(ax,v,C,'Tempo (ms)',titles(k),fontName);
end
figNames(1) = "g3_01_A_tempi";
exportFigure(f,outDir,figNames(1));

%% G2/G3 - B: comandi; C: livelli. Categorie equidistanti, nessun fit.
for taskIndex = 1:2
    if taskIndex == 1
        task = "b"; conditions = ["1","3","5"]; xlab = 'Comandi';
        figNumber = 2; name = "g3_02_B_tempi";
    else
        task = "c"; conditions = ["L1","L2","L3","L4","L5"]; xlab = 'Livello';
        figNumber = 3; name = "g3_03_C_tempi";
    end
    [f,t] = makeFigure(1,2,14.5,7.3);
    for k = 1:2
        ax = nexttile(t); v = cell(2,numel(conditions));
        for m = 1:2
            for j = 1:numel(conditions)
                v{m,j} = timeValues(T,task,metrics(k),modes(m),conditions(j));
            end
        end
        curveComparison(ax,conditions,v,C,'Tempo (ms)',titles(k),xlab,fontName);
    end
    figNames(figNumber) = name;
    exportFigure(f,outDir,name);
end

%% G4 - CPU A/B per richiesta. Ogni pannello ha la propria scala.
[f,t] = makeFigure(1,2,14.5,7.3);
for k = 1:2
    task = ["a","b"]; ax = nexttile(t); v = cell(1,2);
    for m = 1:2
        v{m} = resourceValues(R,task(k),"cpu_seconds_per_request",modes(m),"all",1000);
    end
    barComparison(ax,v,C,'CPU (ms/richiesta)',"Task " + upper(task(k)),fontName);
end
figNames(4) = "g3_04_AB_cpu";
exportFigure(f,outDir,figNames(4));

%% G5 - A/B, totale cgroup e anonima: componenti NON additive fra pannelli.
[f,t] = makeFigure(2,2,14.5,12.5);
keys = ["memory_mean_mib","memory_anon_mean_mib"];
memTitles = ["Totale cgroup","Anonima"];
for k = 1:2
    tasks = ["a","b"];
    for col = 1:2
        ax = nexttile(t); v = cell(1,2);
        for m = 1:2
            v{m} = resourceValues(R,tasks(k),keys(col),modes(m),"all",1);
        end
        barComparison(ax,v,C,'Memoria (MiB)', ...
            "Task " + upper(tasks(k)) + " - " + memTitles(col),fontName);
    end
end
figNames(5) = "g3_05_AB_memoria";
exportFigure(f,outDir,figNames(5));

%% G6 - C CPU per richiesta
levels = ["L1","L2","L3","L4","L5"];
[f,t] = makeFigure(1,1,14,7.8);
ax = nexttile(t); v = cell(2,5);
for m = 1:2
    for j = 1:5
        v{m,j} = resourceValues(R,"c","cpu_seconds_per_request",modes(m),levels(j),1000);
    end
end
curveComparison(ax,levels,v,C,'CPU (ms/richiesta)', ...
    'Task C - lavoro CPU sul Raspberry','Livello',fontName);
figNames(6) = "g3_06_C_cpu";
exportFigure(f,outDir,figNames(6));

%% G7 - C memoria totale e anonima
[f,t] = makeFigure(1,2,14.5,7.3);
for k = 1:2
    ax = nexttile(t); v = cell(2,5);
    for m = 1:2
        for j = 1:5
            v{m,j} = resourceValues(R,"c",keys(k),modes(m),levels(j),1);
        end
    end
    curveComparison(ax,levels,v,C,'Memoria (MiB)',memTitles(k),'Livello',fontName);
end
figNames(7) = "g3_07_C_memoria";
exportFigure(f,outDir,figNames(7));

%% G8 - B movimento: n=1 per modalita', nessuna SD o barra di errore.
[f,t] = makeFigure(1,3,15.5,8);
title(t,{'B - sequenza S5_01','Una prova per modalita''; nessuna barra di errore'}, ...
    'FontName',fontName,'FontSize',10,'Interpreter','none');
motionKeys = ["http_s","execution_s","total_s"];
motionTitles = ["Richiesta HTTP","Esecuzione e arresti","Totale"];
for k = 1:3
    ax = nexttile(t); hold(ax,'on'); y = zeros(1,2);
    for m = 1:2
        q = M(M.task == "b" & M.mode == modes(m),:);
        assert(height(q)==1 && str2double(q.observations)==1);
        y(m) = str2double(q.(char(motionKeys(k))));
        bar(ax,m,y(m),0.6,'FaceColor',lightColor(C(m,:)),'EdgeColor',C(m,:));
        text(ax,m,y(m),sprintf('%.3f',y(m)),'HorizontalAlignment','center', ...
            'VerticalAlignment','bottom','FontSize',8,'FontName',fontName);
    end
    set(ax,'XTick',[1 2],'XTickLabel',{'LOCAL','REMOTE'});
    xtickangle(ax,20); xlim(ax,[0.4 2.6]);
    styleAxes(ax,'Tempo reale (s)',motionTitles(k),fontName,max(y)*1.23);
end
figNames(8) = "g3_08_B_movimento";
exportFigure(f,outDir,figNames(8));

%% G9 - Mappa in coordinate metriche; sfondo vettoriale per righe occupate.
P = readStrings(fullfile(dataDir,'C_L1_percorso.csv'));
Q = readStrings(fullfile(dataDir,'C_L1_tracce.csv'));
map = jsondecode(fileread(fullfile(dataDir,'L1_mappa.json')));
assert(height(P)==61,'Percorso L1 inatteso.');
assert(sum(Q.mode=="local")==847 && sum(Q.mode=="remote")==847, ...
    'Attesi 847 campioni di traccia per modalita''.');
[f,t] = makeFigure(1,1,14,10);
ax = nexttile(t); hold(ax,'on');
s = double(map.resolution); x0 = double(map.origin(1)); y0 = double(map.origin(2));
G = double(map.grid);
assert(isequal(size(G),[200 200]),'Griglia L1 inattesa.');
% Una patch per ciascun tratto contiguo occupato di riga. Coordinate ai bordi.
for row = 1:size(G,1)
    edges = diff([0 double(G(row,:)==1) 0]);
    starts = find(edges==1); stops = find(edges==-1)-1;
    for k = 1:numel(starts)
        xa = x0+(starts(k)-1)*s; xb = x0+stops(k)*s;
        ya = y0+(row-1)*s; yb = y0+row*s;
        patch(ax,[xa xb xb xa],[ya ya yb yb],[0.82 0.82 0.82], ...
            'EdgeColor','none','HandleVisibility','off');
    end
end
px = str2double(P.x_m); py = str2double(P.y_m);
h = gobjects(1,5);
h(1) = plot(ax,px,py,'k--','LineWidth',1.1);
styles = {'-',':'};
for m = 1:2
    q = Q(Q.mode==modes(m),:);
    h(m+1) = plot(ax,str2double(q.x_m),str2double(q.y_m),styles{m}, ...
        'Color',C(m,:),'LineWidth',1.5);
end
h(4) = plot(ax,px(1),py(1),'ko','MarkerSize',6,'MarkerFaceColor','white');
h(5) = plot(ax,px(end),py(end),'k*','MarkerSize',9);
allX = [px; str2double(Q.x_m)]; allY = [py; str2double(Q.y_m)];
axis(ax,'equal'); xlim(ax,[min(allX)-0.5 max(allX)+0.5]);
ylim(ax,[min(allY)-0.5 max(allY)+0.5]);
xlabel(ax,'x (m)'); ylabel(ax,'y (m)');
title(ax,'C L1 - griglia e tracce odometriche','Interpreter','none');
set(ax,'FontName',fontName,'FontSize',9,'Box','on');
legend(ax,h,{'A* (centri celle)','Odometria LOCAL','Odometria REMOTE', ...
    'Cella iniziale','Obiettivo'},'Location','southoutside','NumColumns',2, ...
    'Interpreter','none','FontSize',8);
figNames(9) = "g3_09_C_traiettoria";
exportFigure(f,outDir,figNames(9));

%% File da riconsegnare: una cartella e uno ZIP, senza modificare gli input.
writetable(TS,fullfile(outDir,'riepilogo_tempi_ms.csv'));
writetable(RS,fullfile(outDir,'riepilogo_risorse.csv'));
fid = fopen(fullfile(outDir,'METODO_E_VERSIONE.txt'),'w');
assert(fid~=-1,'Impossibile scrivere il riepilogo.');
fprintf(fid,'MATLAB: %s\nGenerazione: %s\n',version,runID);
fprintf(fid,'G1-G7: 5 repliche; media e SD campionaria (n-1). Non IC95%%.\n');
fprintf(fid,'G8-G9: 1 prova per modalita'', nessuna barra statistica.\n');
fprintf(fid,'CPU = tempo cumulativo Raspberry per richiesta, non energia.\n');
fprintf(fid,'RAM = media temporale di finestra, totale cgroup/anonima.\n');
fprintf(fid,'Dati originali e selezione: dati_grafici/provenienza.json.\n');
fprintf(fid,'Tracce C L1 odometriche; nessuna verifica collisioni ground-truth.\n');
fclose(fid);
for k = 1:9
    info = dir(fullfile(outDir,[char(figNames(k)) '.pdf']));
    assert(numel(info)==1 && info.bytes>1000,'PDF mancante o vuoto.');
end
files = dir(outDir); files = files(~[files.isdir]);
zipPath = fullfile(baseDir,['grafici_tesi_' runID '.zip']);
zip(zipPath,{files.name},outDir);
fprintf('\nCOMPLETATO: 9 PDF, 9 PNG e 9 FIG.\nCartella: %s\nZIP: %s\n',outDir,zipPath);
fprintf('Scaricare lo ZIP e inviarlo per la verifica visiva prima di Overleaf.\n');
end

function T = readStrings(path)
assert(isfile(path),'File mancante: %s',path);
opts = detectImportOptions(path,'Delimiter',',','TextType','string');
opts = setvartype(opts,opts.VariableNames,'string');
T = readtable(path,opts);
end

function v = timeValues(T,task,metric,mode,condition)
q = T(T.task==task & T.metric==metric & T.mode==mode & T.condition==condition,:);
[~,idx] = sort(str2double(q.replicate)); q = q(idx,:);
assert(height(q)==5 && isequal(str2double(q.replicate)',1:5), ...
    'Gruppo temporale incompleto: %s %s %s %s',task,metric,mode,condition);
v = str2double(q.value); assert(all(isfinite(v) & v>0));
end

function v = resourceValues(R,task,key,mode,level,factor)
q = R(R.task==task & R.mode==mode & R.level==level,:);
[~,idx] = sort(str2double(q.replicate)); q = q(idx,:);
assert(height(q)==5 && isequal(str2double(q.replicate)',1:5), ...
    'Gruppo risorse incompleto: %s %s %s',task,mode,level);
v = str2double(q.(char(key)))*factor;
assert(all(isfinite(v) & v>=0));
end

function validateSummaries(T,R,TS,RS)
assert(height(TS)==36 && height(RS)==14,'Numero di gruppi inatteso.');
for i = 1:height(TS)
    v = timeValues(T,TS.task(i),TS.metric(i),TS.mode(i),TS.condition(i));
    assert(abs(mean(v)-str2double(TS.mean(i)))<1e-8,'Media tempi incoerente.');
    assert(abs(std(v,0)-str2double(TS.sd(i)))<1e-8,'SD tempi incoerente.');
end
keys = ["cpu_seconds_per_request","memory_mean_mib","memory_anon_mean_mib"];
for i = 1:height(RS)
    for k = 1:numel(keys)
        v = resourceValues(R,RS.task(i),keys(k),RS.mode(i),RS.level(i),1);
        assert(abs(mean(v)-str2double(RS.(char(keys(k)+"_mean"))(i)))<1e-8, ...
            'Media risorse incoerente.');
        assert(abs(std(v,0)-str2double(RS.(char(keys(k)+"_sd"))(i)))<1e-8, ...
            'SD risorse incoerente.');
    end
end
fprintf('Controlli dati superati: 36 gruppi temporali e 14 gruppi risorse.\n');
end

function [f,t] = makeFigure(rows,cols,widthCm,heightCm)
f = figure('Color','white','Units','centimeters', ...
    'Position',[2 2 widthCm heightCm],'NumberTitle','off');
t = tiledlayout(f,rows,cols,'TileSpacing','compact','Padding','compact');
end

function barComparison(ax,v,C,ylab,ttl,fontName)
hold(ax,'on'); top = 0;
for m = 1:2
    assert(numel(v{m})==5); mu = mean(v{m}); sd = std(v{m},0);
    bar(ax,m,mu,0.6,'FaceColor',lightColor(C(m,:)),'EdgeColor',C(m,:));
    errorbar(ax,m,mu,sd,'Color',C(m,:),'LineStyle','none','CapSize',6,'LineWidth',1);
    scatter(ax,m+(-2:2)'*0.035,v{m},15,C(m,:),'filled');
    top = max([top; v{m}(:); mu+sd]);
end
set(ax,'XTick',[1 2],'XTickLabel',{'LOCAL','REMOTE'});xlim(ax,[0.4 2.6]);
styleAxes(ax,ylab,ttl,fontName,top*1.15);
end

function curveComparison(ax,categories,v,C,ylab,ttl,xlab,fontName)
hold(ax,'on'); x = 1:numel(categories); h = gobjects(1,2); top = 0;
markers = {'o','s'}; styles = {'-','--'};
for m = 1:2
    mu = cellfun(@mean,v(m,:)); sd = cellfun(@(z)std(z,0),v(m,:));
    h(m) = errorbar(ax,x,mu,sd,'Color',C(m,:),'Marker',markers{m}, ...
        'LineStyle',styles{m},'LineWidth',1.1,'CapSize',5,'MarkerSize',4);
    shift = (2*m-3)*0.06;
    for j = 1:numel(categories)
        scatter(ax,j+shift+(-2:2)'*0.015,v{m,j},10,C(m,:),'filled', ...
            'HandleVisibility','off');
        top = max([top; v{m,j}(:); mu(j)+sd(j)]);
    end
end
set(ax,'XTick',x,'XTickLabel',cellstr(categories));
xlim(ax,[0.7 numel(categories)+0.3]);xlabel(ax,xlab,'Interpreter','none');
styleAxes(ax,ylab,ttl,fontName,top*1.15);
legend(ax,h,{'LOCAL','REMOTE'},'Location','best','FontSize',8);
end

function styleAxes(ax,ylab,ttl,fontName,top)
ylabel(ax,ylab,'Interpreter','none');title(ax,ttl,'Interpreter','none');
ylim(ax,[0 max(top,eps)]);grid(ax,'on');
set(ax,'FontName',fontName,'FontSize',9,'Box','on','GridAlpha',0.15, ...
    'XGrid','off','YGrid','on','Layer','top');
end

function col = lightColor(col)
col = 0.58*[1 1 1]+0.42*col;
end

function exportFigure(f,outDir,name)
drawnow;
exportgraphics(f,fullfile(outDir,[char(name) '.pdf']), ...
    'ContentType','vector','BackgroundColor','white');
exportgraphics(f,fullfile(outDir,[char(name) '.png']), ...
    'Resolution',300,'BackgroundColor','white');
savefig(f,fullfile(outDir,[char(name) '.fig']));
fprintf('Esportato: %s\n',name);
end
