# Get the frequency information of the measurement set
ms.open(vis)
rec = ms.getdata(['axis_info'])
df,f0 = (rec['axis_info']['freq_axis']['resolution'][len(rec['axis_info']['freq_axis']['resolution'])/2],rec['axis_info']['freq_axis']['chan_freq'][len(rec['axis_info']['freq_axis']['resolution'])/2])
F =rec['axis_info']['freq_axis']['chan_freq'].squeeze()/1e6
df=df[0]*len(rec['axis_info']['freq_axis']['resolution'])
f0=f0[0]
rec_time=ms.getdata(['time'])
sectime=qa.quantity(rec_time['time'][0],unitname='s')

freq=str(f0/1.e6)+'MHz'
bandwidth=str(df)+'Hz'
outname='pica_'+freq+'.im'
outnt2='pica_'+freq+'_nt2.im'

# Generate scaled image at correct frequency
exp='IM0/((332926757/'+str(f0)+')^(IM1))'
immath(imagename=['pica_vla333.fits','pica_spec_index.fits'],mode='evalexpr',expr=exp,outfile=outname)
imhead(outname,mode='put',hdkey='crval3',hdvalue=freq)
imhead(outname,mode='put',hdkey='cdelt3',hdvalue=bandwidth)
imhead(outname,mode='put',hdkey='date-obs',hdvalue=qa.time(sectime,form=["ymd"]))

# Generate 2nd Taylor term
immath(imagename=[outname,'pica_spec_index.fits'],mode='evalexpr',outfile=outnt2, expr='(IM1*IM0)')
imhead(outnt2,mode='put',hdkey='crval3',hdvalue=freq)
imhead(outnt2,mode='put',hdkey='cdelt3',hdvalue=bandwidth)
imhead(outnt2,mode='put',hdkey='date-obs',hdvalue=qa.time(sectime,form=["ymd"]))

ft(vis=vis,model=[outname,outnt2],nterms=2,reffreq=freq)
