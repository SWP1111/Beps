document.addEventListener('DOMContentLoaded', () => {
    
    // 테스트용 데이터
    const data = {
      '삼안': {
        '기획팀': [
            {id: 'b0001', name: '홍길동', position: '대리', progress: 0.15},
            {id: 'b0002', name: '김철수', position: '사원', progress: 0.25},
            {id: 'b0003', name: '이영희', position: '대리', progress: 0.35},
            {id: 'b0004', name: '박진수', position: '사원', progress: 0.45},
            {id: 'b0004',name: '최유리', position: '대리', progress: 0.55},
            {id: 'b0019',name: '김혜인', position: '선임', progress: 0.65},
            {id: 'b0020',name: '이태윤', position: '사원', progress: 0.75},
        ],
        '설계팀': [
            {id: 'b0003', name: '이영희', position: '대리', progress: 0.35},
            {id: 'b0004', name: '박진수', position: '사원', progress: 0.45},
        ]
      },
      '한맥': {
        '개발팀': [
            {id: 'b0004',name: '최유리', position: '대리', progress: 0.55},
        ],
        '운영팀': [
            {id: 'b0005',name: '정해인', position: '사원', progress: 0.65},
            {id: 'b0006',name: '박보검', position: '사원', progress: 0.75},
        ]
      },
      '바론': {
        '개발팀': [{id: 'b0007',name: '최유리', position: '대리', progress: 0.55},],
        '운영팀': [ 
            {id: 'b0008',name: '정해인', position: '사원', progress: 0.65},
            {id: 'b0009',name: '박보검', position: '사원', progress: 0.75},
        ]
      },
      '장헌': {
        '개발팀': [{id: 'b0010',name: '최유리', position: '대리', progress: 0.55},],
        '운영팀': [ {id: 'b0011',name: '정해인', position: '사원', progress: 0.65},
            {id: 'b0012',name: '박보검', position: '사원', progress: 0.75},]
      },
      '한라': {
        '개발팀': [{id: 'b0013',name: '최유리', position: '대리', progress: 0.55},],
        '운영팀': [ {id: 'b0014',name: '정해인', position: '사원', progress: 0.65},
            {id: 'b0015',name: '박보검', position: '사원', progress: 0.75},]
      },
      'PTC': {
        '개발팀': [{id: 'b0016',name: '최유리', position: '대리', progress: 0.55},],
        '운영팀': [ {id: 'b0017',name: '정해인', position: '사원', progress: 0.65},
            {id: 'b0018',name: '박보검', position: '사원', progress: 0.75},]
      },
      '기술개발센터': {
        '그래픽스 개발팀': [
            {id: 'b23009',name: '정나래', position: '선임', progress: 0.65},
            {id: 'b23042',name: '한성일', position: '책임', progress: 0.75},
        ],
        '기술기획팀': [
            {id: 'b0019',name: '김혜인', position: '선임', progress: 0.65},
            {id: 'b0020',name: '이태윤', position: '사원', progress: 0.75},
        ],
      },
      '총괄기획실': {
       '개발팀': [{id: 'b0021',name: '최유리', position: '대리', progress: 0.55},],
        '운영팀': [ {nid: 'b0022',ame: '정해인', position: '사원', progress: 0.65},
            {id: 'b0023',name: '박보검', position: '사원', progress: 0.75},]
      },
      '기타': {
       '개발팀': [{id: 'b0024',name: '최유리', position: '대리', progress: 0.55},],
        '운영팀': [ {id: 'b0025',name: '정해인', position: '사원', progress: 0.65},
            {id: 'b0026',name: '박보검', position: '사원', progress: 0.75},]
      },
    };

    const container = document.getElementById('container');

    // #region scrollbar 동작 
    const thumb = document.querySelector('.custom-scrollbar-thumb');
    const scrollbar = document.querySelector('.custom-scrollbar');

    const updateThumbHeight = () => {
        const scrollable = container.scrollHeight - container.clientHeight;
        if (scrollable <= 0) {
          thumb.style.display = 'none'; // 스크롤 안 생기면 숨김
        } else {
          thumb.style.display = 'block';
          const ratio = container.clientHeight / container.scrollHeight;
          const height = ratio * scrollbar.clientHeight;
          thumb.style.height = `${height}px`;
        }
    };

    const updateThumbPosition = () => {
      const ratio = container.scrollTop / (container.scrollHeight - container.clientHeight);
      const maxTop = scrollbar.clientHeight - thumb.offsetHeight;
      const top = ratio * maxTop;
      thumb.style.transform = `translateY(${top}px)`;
    };

    const updateThumbVisibility = () => {
        const scrollable = container.scrollHeight > container.clientHeight;
        if (scrollable) {
          scrollbar.style.display = 'block';
          updateThumbHeight();
          updateThumbPosition();
        } else {
          scrollbar.style.display = 'none';
        }
      };

    container.addEventListener('scroll', () => {
      updateThumbHeight();
      updateThumbPosition();
      updateThumbVisibility();
    });

    requestAnimationFrame(() => {
        updateThumbHeight();
        updateThumbPosition();
        updateThumbVisibility ();
      });


     // 👇 드래그 동작 처리
     let isDragging = false;
     let startY, startScrollTop;
 
     thumb.addEventListener('mousedown', (e) => {
       isDragging = true;
       startY = e.clientY;
       startScrollTop = container.scrollTop;
       e.preventDefault();
     });
 
     document.addEventListener('mousemove', (e) => {
       if (!isDragging) return;
       const deltaY = e.clientY - startY;
       const scrollableHeight = container.scrollHeight - container.clientHeight;
       const maxTop = scrollbar.clientHeight - thumb.offsetHeight;
       const scrollRatio = scrollableHeight / maxTop;
       container.scrollTop = startScrollTop + deltaY * scrollRatio;
     });
 
     document.addEventListener('mouseup', () => {
       isDragging = false;
     });
    // #endregion

    let selectedUserId = null;
    let selectedCompany = null;
    let selectedTeam = null;

    const searchInput = document.getElementById('.search');
    const searchIcon = document.getElementById('.search-icon');
    
    function handleSearch() {
      const keyword = searchInput.value.trim().toLowerCase();

      if(keyword === '') {
        renderCompanyList();
      }
      else
        renderSearchResults(keyword);
    }

    function renderSearchResults(keyword) {
      container.innerHTML = '';
    
      const allBtn = document.createElement('button');
      allBtn.innerText = '전체';
      allBtn.classList.add('dimmed');
      allBtn.onclick = () => renderCompanyList();
      container.appendChild(allBtn);
    
      const lowerKeyword = keyword.toLowerCase();
    
      const results = [];
    
      for (const company in data) {
        // 회사 이름에 keyword 포함
        if (company.toLowerCase().includes(lowerKeyword)) {
          results.push({ type: 'company', company });
        }
    
        for (const team in data[company]) {
          // 팀 이름에 keyword 포함
          if (team.toLowerCase().includes(lowerKeyword)) {
            results.push({ type: 'team', company, team });
          }
    
          data[company][team].forEach(user => {
            // 직원 이름에 keyword 포함
            if (user.name.toLowerCase().includes(lowerKeyword)) {
              results.push({ type: 'user', company, team, user });
            }
          });
        }
      }
    
      if (results.length === 0) {
        const empty = document.createElement('div');
        empty.innerText = '검색 결과가 없습니다.';
        container.appendChild(empty);
        return;
      }
    
      results.forEach(result => {
        const btn = document.createElement('button');
    
        if (result.type === 'company') {
          btn.innerText = result.company;
          btn.onclick = () => {
            selectedCompany = result.company;
            selectedTeam = null;
            selectedUserId = null;
            renderTeamList();
          };
        }
    
        if (result.type === 'team') {
          btn.innerText = `${result.company} / ${result.team}`;
          btn.onclick = () => {
            selectedCompany = result.company;
            selectedTeam = result.team;
            selectedUserId = null;
            renderUserList();
          };
        }
    
        if (result.type === 'user') {
          btn.innerText = `${result.company} / ${result.team} / ${result.user.name}`;
          btn.onclick = () => {
            selectedCompany = result.company;
            selectedTeam = result.team;
            selectedUserId = result.user.id;
            renderUserList();
          };
        }
    
        container.appendChild(btn);
      });
    
      updateThumbVisibility();
    }

    searchInput.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        handleSearch();
      }
    });

    searchIcon.addEventListener('click', handleSearch);

    const renderCompanyList = () => {
      selectedCompany = null;
      selectedTeam = null;
      selectedUserId = null;
      container.innerHTML = '';

      const allBtn = document.createElement('button');
      allBtn.innerText = '전체';
      allBtn.classList.add('selected');
      allBtn.onclick = () => renderCompanyList();
      container.appendChild(allBtn);

      Object.keys(data).forEach(company => {
        const btn = document.createElement('button');
        btn.innerText = company;
        btn.onclick = () => {
          selectedCompany = company;
          renderTeamList();
        };
        container.appendChild(btn);
      });

      updateThumbVisibility(); 
    };

    const renderTeamList = () => {
        container.innerHTML = '';

        const allBtn = document.createElement('button');
        allBtn.innerText = '전체';
        allBtn.classList.add('dimmed');
        allBtn.onclick = () => renderCompanyList();
        container.appendChild(allBtn);

        const companyBtn = document.createElement('button');
        companyBtn.innerText = selectedCompany;
        companyBtn.classList.add('selected');
        companyBtn.onclick = () => renderTeamList();
        container.appendChild(companyBtn);

        Object.keys(data[selectedCompany]).forEach(team => {
          const btn = document.createElement('button');
          btn.innerText = team;
          btn.onclick = () => {
            selectedTeam = team;
            selectedUserId = null;
            renderUserList();
          };
          if (team === selectedTeam) btn.classList.add('selected');
          container.appendChild(btn);
        });

        updateThumbVisibility(); 
      };

    const renderUserList = () => {
      container.innerHTML = '';

      const allBtn = document.createElement('button');
      allBtn.innerText = '전체';
      allBtn.classList.add('dimmed');
      allBtn.onclick = () => renderCompanyList();
      container.appendChild(allBtn);

      const companyBtn = document.createElement('button');
      companyBtn.innerText = selectedCompany;
      companyBtn.classList.add('dimmed');
      companyBtn.onclick = () => 
      {
        selectedTeam = null;
        selectedUserId = null;
        renderTeamList();
      }
      container.appendChild(companyBtn);

      const teamBtn = document.createElement('button');
      teamBtn.innerText = selectedTeam;
      teamBtn.classList.add('selected');
      teamBtn.onclick = () => 
      {
        selectedUserId = null;
        renderTeamList();
        renderUserList();
      }
      container.appendChild(teamBtn);

      data[selectedCompany][selectedTeam].forEach(user => {
        const btn = document.createElement('button');
        btn.className='user-button';

        const text = document.createElement('span');
        text.className = 'text';
        text.innerText = `${user.name} ${user.position}`;
        btn.appendChild(text);

        if(user.progress <= 0.2)
        {
            const reddot = document.createElement('span');
            reddot.className = 'dot';
            btn.appendChild(reddot);
        }

        if (user.id === selectedUserId)
        {
            teamBtn.classList.add('dimmed');
            btn.classList.add('selected');
        }
        btn.onclick = () => {
            selectedUserId = user.id;
          renderUserList();
        };
        container.appendChild(btn);
      });

      updateThumbVisibility(); 
    };

    
    renderCompanyList();

  });